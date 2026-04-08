import os
import pytz
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")
tz = pytz.timezone(TIMEZONE)

client = None
db = None

async def init_db():
    global client, db

    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URL") or os.environ.get("DATABASE_URL")

    print("=" * 50)
    print("🔍 ENV CHECK:")
    print(f"  MONGODB_URI = {os.environ.get('MONGODB_URI', 'NOT SET')[:40] if os.environ.get('MONGODB_URI') else 'NOT SET'}")
    print(f"  MONGO_URL   = {os.environ.get('MONGO_URL', 'NOT SET')[:40] if os.environ.get('MONGO_URL') else 'NOT SET'}")
    print(f"  URI found   = {'YES → ' + uri[:40] if uri else 'NO - WILL FAIL'}")
    print("=" * 50)

    if not uri:
        raise ValueError("MONGODB_URI is empty or not set in Railway environment variables!")

    client = AsyncIOMotorClient(
        uri,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        tls=True,
        tlsAllowInvalidCertificates=False
    )
    db = client["sales_bot"]

    # Test connection
    await client.admin.command("ping")
    print("✅ MongoDB ping successful!")

    # Create indexes
    await db.sales.create_index("order_id", unique=True)
    await db.sales.create_index("buyer_username")
    await db.sales.create_index("created_at")
    await db.customers.create_index("username", unique=True)
    await db.products.create_index("name", unique=True)
    await db.tickets.create_index("ticket_id", unique=True)
    print("✅ MongoDB connected and indexes created.")

def now():
    return datetime.now(tz)

# ─── ORDER ID ───────────────────────────────────────────────
async def generate_order_id():
    counter = await db.counters.find_one_and_update(
        {"_id": "order_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"ORD{counter['seq']:05d}"

async def generate_ticket_id():
    counter = await db.counters.find_one_and_update(
        {"_id": "ticket_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"TKT{counter['seq']:04d}"

# ─── PRODUCTS ────────────────────────────────────────────────
async def add_product(name, cost_price, sell_price, stock=0, category="general", duration_options=None):
    await db.products.update_one(
        {"name": name.lower()},
        {"$set": {
            "name": name.lower(),
            "display_name": name,
            "cost_price": cost_price,
            "sell_price": sell_price,
            "stock": stock,
            "category": category,
            "duration_options": duration_options or {},
            "active": True,
            "updated_at": now()
        }},
        upsert=True
    )

async def get_all_products(active_only=True):
    query = {"active": True} if active_only else {}
    return await db.products.find(query).to_list(None)

async def get_product(name):
    return await db.products.find_one({"name": name.lower()})

async def update_product_stock(name, delta):
    await db.products.update_one(
        {"name": name.lower()},
        {"$inc": {"stock": delta}, "$set": {"updated_at": now()}}
    )

async def delete_product(name):
    await db.products.update_one({"name": name.lower()}, {"$set": {"active": False}})

async def get_low_stock_products(threshold):
    return await db.products.find({"stock": {"$lte": threshold}, "active": True}).to_list(None)

# ─── SALES ───────────────────────────────────────────────────
async def log_sale(buyer_username, product_name, sell_price, cost_price,
                   payment_mode="upi", duration=None, notes="", credentials=""):
    order_id = await generate_order_id()
    profit = sell_price - cost_price
    sale = {
        "order_id": order_id,
        "buyer_username": buyer_username.lstrip("@").lower(),
        "product_name": product_name.lower(),
        "sell_price": sell_price,
        "cost_price": cost_price,
        "profit": profit,
        "payment_mode": payment_mode,
        "duration": duration,
        "credentials": credentials,
        "notes": notes,
        "status": "delivered",
        "created_at": now(),
        "refunded": False
    }
    await db.sales.insert_one(sale)
    await update_product_stock(product_name, -1)
    await upsert_customer(buyer_username, sell_price)
    return order_id, profit

async def get_sale(order_id):
    return await db.sales.find_one({"order_id": order_id})

async def update_sale_status(order_id, status):
    await db.sales.update_one({"order_id": order_id}, {"$set": {"status": status}})

async def refund_sale(order_id):
    sale = await get_sale(order_id)
    if sale and not sale.get("refunded"):
        await db.sales.update_one({"order_id": order_id}, {"$set": {"refunded": True, "status": "refunded"}})
        await update_product_stock(sale["product_name"], 1)
        return sale
    return None

async def get_sales_by_period(start, end=None):
    query = {"created_at": {"$gte": start}}
    if end:
        query["created_at"]["$lte"] = end
    return await db.sales.find(query).sort("created_at", -1).to_list(None)

async def get_all_sales(limit=50, skip=0):
    return await db.sales.find().sort("created_at", -1).skip(skip).limit(limit).to_list(None)

async def get_sales_stats(start=None):
    match = {}
    if start:
        match["created_at"] = {"$gte": start}
    match["refunded"] = False
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$sell_price"},
            "total_cost": {"$sum": "$cost_price"},
            "total_profit": {"$sum": "$profit"},
            "total_orders": {"$sum": 1}
        }}
    ]
    result = await db.sales.aggregate(pipeline).to_list(None)
    return result[0] if result else {"total_revenue": 0, "total_cost": 0, "total_profit": 0, "total_orders": 0}

async def get_best_selling_products(limit=5, start=None):
    match = {"refunded": False}
    if start:
        match["created_at"] = {"$gte": start}
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$product_name", "count": {"$sum": 1}, "revenue": {"$sum": "$sell_price"}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    return await db.sales.aggregate(pipeline).to_list(None)

async def get_payment_mode_stats(start=None):
    match = {"refunded": False}
    if start:
        match["created_at"] = {"$gte": start}
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$payment_mode", "count": {"$sum": 1}, "total": {"$sum": "$sell_price"}}},
        {"$sort": {"count": -1}}
    ]
    return await db.sales.aggregate(pipeline).to_list(None)

async def search_sales(buyer_username=None, product_name=None, order_id=None):
    query = {}
    if buyer_username:
        query["buyer_username"] = buyer_username.lstrip("@").lower()
    if product_name:
        query["product_name"] = product_name.lower()
    if order_id:
        query["order_id"] = order_id.upper()
    return await db.sales.find(query).sort("created_at", -1).limit(20).to_list(None)

# ─── CUSTOMERS ───────────────────────────────────────────────
async def upsert_customer(username, amount_spent):
    username = username.lstrip("@").lower()
    await db.customers.update_one(
        {"username": username},
        {
            "$inc": {"total_spent": amount_spent, "total_orders": 1},
            "$set": {"last_purchase": now()},
            "$setOnInsert": {"joined_at": now(), "blacklisted": False, "vip": False, "notes": "", "wallet": 0}
        },
        upsert=True
    )

async def get_customer(username):
    return await db.customers.find_one({"username": username.lstrip("@").lower()})

async def get_all_customers():
    return await db.customers.find().sort("total_spent", -1).to_list(None)

async def get_top_customers(limit=10):
    return await db.customers.find({"blacklisted": False}).sort("total_spent", -1).limit(limit).to_list(None)

async def blacklist_customer(username, value=True):
    await db.customers.update_one({"username": username.lstrip("@").lower()}, {"$set": {"blacklisted": value}})

async def set_vip(username, value=True):
    await db.customers.update_one({"username": username.lstrip("@").lower()}, {"$set": {"vip": value}})

async def add_customer_note(username, note):
    await db.customers.update_one({"username": username.lstrip("@").lower()}, {"$set": {"notes": note}})

async def get_inactive_customers(days=30):
    cutoff = now() - timedelta(days=days)
    return await db.customers.find({"last_purchase": {"$lt": cutoff}}).to_list(None)

async def add_wallet_credit(username, amount):
    await db.customers.update_one({"username": username.lstrip("@").lower()}, {"$inc": {"wallet": amount}})

async def use_wallet(username, amount):
    customer = await get_customer(username)
    if customer and customer.get("wallet", 0) >= amount:
        await db.customers.update_one({"username": username.lstrip("@").lower()}, {"$inc": {"wallet": -amount}})
        return True
    return False

# ─── EXPENSES ────────────────────────────────────────────────
async def log_expense(description, amount, category="misc"):
    await db.expenses.insert_one({
        "description": description,
        "amount": amount,
        "category": category,
        "created_at": now()
    })

async def get_expenses(start=None):
    query = {}
    if start:
        query["created_at"] = {"$gte": start}
    return await db.expenses.find(query).sort("created_at", -1).to_list(None)

async def get_expenses_total(start=None):
    match = {}
    if start:
        match["created_at"] = {"$gte": start}
    pipeline = [{"$match": match}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    result = await db.expenses.aggregate(pipeline).to_list(None)
    return result[0]["total"] if result else 0

# ─── DEBTS ───────────────────────────────────────────────────
async def add_debt(buyer_username, amount, product_name, notes=""):
    await db.debts.insert_one({
        "buyer_username": buyer_username.lstrip("@").lower(),
        "amount": amount,
        "product_name": product_name,
        "notes": notes,
        "paid": False,
        "created_at": now()
    })

async def get_unpaid_debts():
    return await db.debts.find({"paid": False}).sort("created_at", -1).to_list(None)

async def mark_debt_paid(debt_id):
    from bson import ObjectId
    await db.debts.update_one({"_id": ObjectId(debt_id)}, {"$set": {"paid": True}})

# ─── SUPPORT TICKETS ─────────────────────────────────────────
async def create_ticket(user_id, username, issue):
    ticket_id = await generate_ticket_id()
    await db.tickets.insert_one({
        "ticket_id": ticket_id,
        "user_id": user_id,
        "username": username.lstrip("@").lower(),
        "issue": issue,
        "status": "open",
        "created_at": now(),
        "resolved_at": None
    })
    return ticket_id

async def get_open_tickets():
    return await db.tickets.find({"status": "open"}).sort("created_at", 1).to_list(None)

async def close_ticket(ticket_id):
    await db.tickets.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": "resolved", "resolved_at": now()}}
    )

async def get_user_tickets(username):
    return await db.tickets.find({"username": username.lstrip("@").lower()}).sort("created_at", -1).to_list(None)

# ─── CREDENTIALS ─────────────────────────────────────────────
async def store_credentials(product_name, email, password, expiry=None, notes=""):
    await db.credentials.insert_one({
        "product_name": product_name.lower(),
        "email": email,
        "password": password,
        "expiry": expiry,
        "assigned": False,
        "assigned_to": None,
        "assigned_at": None,
        "notes": notes,
        "added_at": now()
    })

async def assign_credential(product_name, username):
    cred = await db.credentials.find_one({"product_name": product_name.lower(), "assigned": False})
    if cred:
        await db.credentials.update_one(
            {"_id": cred["_id"]},
            {"$set": {"assigned": True, "assigned_to": username.lstrip("@").lower(), "assigned_at": now()}}
        )
        return cred
    return None

async def get_expiring_credentials(days=3):
    cutoff = now() + timedelta(days=days)
    return await db.credentials.find({"expiry": {"$lte": cutoff}, "assigned": True}).to_list(None)

async def get_credentials_stock():
    pipeline = [
        {"$group": {"_id": "$product_name", "total": {"$sum": 1}, "available": {"$sum": {"$cond": [{"$eq": ["$assigned", False]}, 1, 0]}}}},
        {"$sort": {"_id": 1}}
    ]
    return await db.credentials.aggregate(pipeline).to_list(None)

# ─── COUPONS ─────────────────────────────────────────────────
async def add_coupon(code, discount_percent, max_uses=None, expiry=None):
    await db.coupons.insert_one({
        "code": code.upper(),
        "discount_percent": discount_percent,
        "max_uses": max_uses,
        "uses": 0,
        "expiry": expiry,
        "active": True,
        "created_at": now()
    })

async def validate_coupon(code):
    coupon = await db.coupons.find_one({"code": code.upper(), "active": True})
    if not coupon:
        return None
    if coupon.get("expiry") and coupon["expiry"] < now():
        return None
    if coupon.get("max_uses") and coupon["uses"] >= coupon["max_uses"]:
        return None
    return coupon

async def use_coupon(code):
    await db.coupons.update_one({"code": code.upper()}, {"$inc": {"uses": 1}})

# ─── SUBSCRIPTIONS (for expiry reminders) ────────────────────
async def add_subscription(username, product_name, expiry_date, order_id):
    await db.subscriptions.update_one(
        {"username": username.lstrip("@").lower(), "product_name": product_name.lower()},
        {"$set": {
            "username": username.lstrip("@").lower(),
            "product_name": product_name.lower(),
            "expiry_date": expiry_date,
            "order_id": order_id,
            "reminded": False,
            "updated_at": now()
        }},
        upsert=True
    )

async def get_expiring_subscriptions(days=3):
    now_dt = now()
    cutoff = now_dt + timedelta(days=days)
    return await db.subscriptions.find({
        "expiry_date": {"$gte": now_dt, "$lte": cutoff},
        "reminded": False
    }).to_list(None)

async def get_user_subscriptions(username):
    return await db.subscriptions.find({"username": username.lstrip("@").lower()}).to_list(None)

async def mark_reminded(sub_id):
    from bson import ObjectId
    await db.subscriptions.update_one({"_id": ObjectId(sub_id)}, {"$set": {"reminded": True}})

# ─── BROADCASTS ──────────────────────────────────────────────
async def get_all_user_ids():
    users = await db.users.find({}, {"user_id": 1}).to_list(None)
    return [u["user_id"] for u in users]

async def register_user(user_id, username):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"username": username, "last_seen": now()}, "$setOnInsert": {"joined_at": now()}},
        upsert=True
    )
