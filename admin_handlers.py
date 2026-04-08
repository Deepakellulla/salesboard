from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, CURRENCY, LOW_STOCK_THRESHOLD, BUSINESS_NAME
from database import *
from helpers import *
from datetime import datetime, timedelta
import pytz
from config import TIMEZONE
import io, openpyxl

tz = pytz.timezone(TIMEZONE)

# ─── ADMIN CHECK DECORATOR ──────────────────────────────────
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Admin only!")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper

# ─── ADMIN MENU ─────────────────────────────────────────────
@admin_only
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""
👑 *Admin Panel — {BUSINESS_NAME}*
━━━━━━━━━━━━━━━━━━━━
💼 *Sales*
/sold `@user product price cost` — Log a sale
/quicksold `product price cost` — Quick log (no buyer)
/orders — Recent orders
/orderstatus `ORDID status` — Update order status
/refund `ORDID` — Refund an order
/search `@user or ORDID` — Search orders

📦 *Products*
/addproduct — Add new product
/products — View all products
/editstock `product +/-qty` — Update stock
/lowstock — View low stock items
/deleteproduct `name` — Remove product

👥 *Customers*
/customers — Top customers list
/customer `@username` — Customer profile
/blacklist `@username` — Blacklist customer
/unblacklist `@username` — Remove blacklist
/setvip `@username` — Set VIP
/addnote `@user note` — Add private note
/addwallet `@user amount` — Add wallet credit
/inactive — Inactive customers (30d)

💰 *Finance*
/stats — Today's stats
/statsweek — Weekly stats
/statsmonth — Monthly stats
/statsall — All time stats
/addexpense `desc amount` — Log expense
/expenses — View expenses
/debts — Unpaid debts
/adddebt `@user amount product` — Add debt
/paymentmodes — Payment breakdown

🔑 *Credentials*
/addcred `product email pass expiry` — Add credential
/credstock — Credential inventory
/expiringcreds — Expiring soon

🎟️ *Coupons*
/addcoupon `CODE percent maxuses` — Add coupon
/coupons — View all coupons

🎫 *Support*
/tickets — Open support tickets
/closeticket `TKTID` — Close a ticket

📊 *Reports*
/export — Export sales to Excel
/topselling — Best selling products
/topcustomers — Top buyers
/broadcast `message` — Message all users

⚙️ *Settings*
/settings — View bot settings
"""
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── LOG SALE ────────────────────────────────────────────────
@admin_only
async def cmd_sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /sold @buyer product sell_price cost_price [payment_mode] [duration] [credentials]"""
    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            "📝 Usage: `/sold @buyer product sell_price cost_price [payment_mode] [duration] [credentials]`\n"
            "Example: `/sold @john netflix 149 80 upi \"1 month\" email:pass`",
            parse_mode="Markdown"
        )
        return
    buyer = args[0]
    product = args[1]
    try:
        sell_price = float(args[2])
        cost_price = float(args[3])
    except ValueError:
        await update.message.reply_text("❌ Price must be a number!")
        return

    payment_mode = args[4] if len(args) > 4 else "upi"
    duration = args[5] if len(args) > 5 else None
    credentials = args[6] if len(args) > 6 else ""

    order_id, profit = await log_sale(buyer, product, sell_price, cost_price, payment_mode, duration, "", credentials)

    receipt = sale_receipt(order_id, product, sell_price, profit, buyer.lstrip("@"), payment_mode, credentials)
    await update.message.reply_text(receipt, parse_mode="Markdown")

    # Send receipt to buyer if they're registered
    users = await db.users.find_one({"username": buyer.lstrip("@").lower()})
    if users:
        try:
            cust_receipt = customer_receipt(order_id, product, sell_price, buyer.lstrip("@"), payment_mode, credentials)
            await context.bot.send_message(users["user_id"], cust_receipt, parse_mode="Markdown")
        except Exception:
            pass

@admin_only
async def cmd_quicksold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /quicksold product price cost"""
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: `/quicksold product sell_price cost_price`", parse_mode="Markdown")
        return
    product = args[0]
    try:
        sell_price = float(args[1])
        cost_price = float(args[2])
    except ValueError:
        await update.message.reply_text("❌ Price must be a number!")
        return
    order_id, profit = await log_sale("unknown", product, sell_price, cost_price)
    await update.message.reply_text(
        f"✅ Quick sale logged!\n📦 `{order_id}` | {product.title()} | Profit: {fmt_money(profit)}",
        parse_mode="Markdown"
    )

# ─── ORDERS ─────────────────────────────────────────────────
@admin_only
async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sales = await get_all_sales(limit=10)
    if not sales:
        await update.message.reply_text("No sales yet!")
        return
    text = "📋 *Recent Orders*\n━━━━━━━━━━━━━━━━━━━━\n"
    for s in sales:
        status_icon = "✅" if s["status"] == "delivered" else "🔄" if s["status"] == "pending" else "❌"
        refunded = " 🔴REFUNDED" if s.get("refunded") else ""
        text += f"{status_icon} `{s['order_id']}` | @{s['buyer_username']} | {s['product_name'].title()} | {fmt_money(s['sell_price'])}{refunded}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_orderstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/orderstatus ORDID status`\nStatuses: pending, processing, delivered, completed", parse_mode="Markdown")
        return
    await update_sale_status(args[0].upper(), args[1].lower())
    await update.message.reply_text(f"✅ Order `{args[0].upper()}` updated to *{args[1]}*", parse_mode="Markdown")

@admin_only
async def cmd_refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/refund ORDID`", parse_mode="Markdown")
        return
    sale = await refund_sale(context.args[0].upper())
    if sale:
        await update.message.reply_text(f"🔴 Order `{sale['order_id']}` refunded!\nProduct: {sale['product_name'].title()}\nAmount: {fmt_money(sale['sell_price'])}", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Order not found or already refunded!")

@admin_only
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/search @username` or `/search ORDID` or `/search productname`", parse_mode="Markdown")
        return
    query = context.args[0]
    if query.startswith("@"):
        sales = await search_sales(buyer_username=query)
    elif query.upper().startswith("ORD"):
        sales = await search_sales(order_id=query)
    else:
        sales = await search_sales(product_name=query)

    if not sales:
        await update.message.reply_text("No results found!")
        return
    text = f"🔍 *Search Results for {query}*\n━━━━━━━━━━━━━━━━━━━━\n"
    for s in sales[:10]:
        text += f"`{s['order_id']}` | @{s['buyer_username']} | {s['product_name'].title()} | {fmt_money(s['sell_price'])} | {fmt_date_short(s['created_at'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── PRODUCTS ────────────────────────────────────────────────
@admin_only
async def cmd_addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: `/addproduct name cost_price sell_price [stock] [category]`\n"
            "Example: `/addproduct Netflix 70 149 10 ott`",
            parse_mode="Markdown"
        )
        return
    name = args[0]
    cost = float(args[1])
    sell = float(args[2])
    stock = int(args[3]) if len(args) > 3 else 0
    category = args[4] if len(args) > 4 else "general"
    await add_product(name, cost, sell, stock, category)
    await update.message.reply_text(f"✅ Product *{name}* added!\nCost: {fmt_money(cost)} | Sell: {fmt_money(sell)} | Stock: {stock}", parse_mode="Markdown")

@admin_only
async def cmd_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = await get_all_products()
    if not products:
        await update.message.reply_text("No products added yet!")
        return
    text = "📦 *Product Catalog*\n━━━━━━━━━━━━━━━━━━━━\n"
    for p in products:
        stock_icon = "🔴" if p["stock"] <= LOW_STOCK_THRESHOLD else "🟢"
        text += f"{stock_icon} *{p['display_name']}* | Cost: {fmt_money(p['cost_price'])} | Sell: {fmt_money(p['sell_price'])} | Stock: {p['stock']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_editstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/editstock productname +5` or `/editstock productname -2`", parse_mode="Markdown")
        return
    product_name = args[0]
    try:
        delta = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Use +5 or -3 format!")
        return
    await update_product_stock(product_name, delta)
    p = await get_product(product_name)
    if p:
        await update.message.reply_text(f"✅ Stock updated! *{product_name.title()}* now has *{p['stock']}* units.", parse_mode="Markdown")

@admin_only
async def cmd_lowstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = await get_low_stock_products(LOW_STOCK_THRESHOLD)
    if not items:
        await update.message.reply_text("✅ All products have sufficient stock!")
        return
    text = f"⚠️ *Low Stock Alert* (≤{LOW_STOCK_THRESHOLD} units)\n━━━━━━━━━━━━━━━━━━━━\n"
    for p in items:
        text += f"🔴 *{p['display_name']}* — {p['stock']} left\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_deleteproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/deleteproduct productname`", parse_mode="Markdown")
        return
    await delete_product(" ".join(context.args))
    await update.message.reply_text(f"🗑️ Product *{' '.join(context.args).title()}* removed!", parse_mode="Markdown")

# ─── STATS ───────────────────────────────────────────────────
@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    s = await get_sales_stats(start=today)
    e = await get_expenses_total(start=today)
    await update.message.reply_text(stats_block("Today's", s["total_revenue"], s["total_cost"], s["total_profit"], s["total_orders"], e), parse_mode="Markdown")

@admin_only
async def cmd_statsweek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = datetime.now(tz) - timedelta(days=7)
    s = await get_sales_stats(start=start)
    e = await get_expenses_total(start=start)
    await update.message.reply_text(stats_block("Weekly", s["total_revenue"], s["total_cost"], s["total_profit"], s["total_orders"], e), parse_mode="Markdown")

@admin_only
async def cmd_statsmonth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = datetime.now(tz) - timedelta(days=30)
    s = await get_sales_stats(start=start)
    e = await get_expenses_total(start=start)
    await update.message.reply_text(stats_block("Monthly", s["total_revenue"], s["total_cost"], s["total_profit"], s["total_orders"], e), parse_mode="Markdown")

@admin_only
async def cmd_statsall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = await get_sales_stats()
    e = await get_expenses_total()
    await update.message.reply_text(stats_block("All Time", s["total_revenue"], s["total_cost"], s["total_profit"], s["total_orders"], e), parse_mode="Markdown")

@admin_only
async def cmd_paymentmodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await get_payment_mode_stats()
    text = "💳 *Payment Mode Breakdown*\n━━━━━━━━━━━━━━━━━━━━\n"
    for s in stats:
        text += f"• {s['_id'].upper()}: {s['count']} orders | {fmt_money(s['total'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── CUSTOMERS ───────────────────────────────────────────────
@admin_only
async def cmd_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    customers = await get_top_customers(10)
    if not customers:
        await update.message.reply_text("No customers yet!")
        return
    text = "👥 *Top Customers*\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, c in enumerate(customers, 1):
        vip = "👑" if c.get("vip") else ""
        text += f"{i}. @{c['username']} {vip} | {c['total_orders']} orders | {fmt_money(c['total_spent'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/customer @username`", parse_mode="Markdown")
        return
    c = await get_customer(context.args[0])
    if not c:
        await update.message.reply_text("❌ Customer not found!")
        return
    sales = await search_sales(buyer_username=context.args[0])
    vip = "👑 VIP" if c.get("vip") else ""
    bl = "🚫 BLACKLISTED" if c.get("blacklisted") else ""
    text = f"""
👤 *Customer Profile*
━━━━━━━━━━━━━━━━━━━━
Username  : @{c['username']} {vip} {bl}
Orders    : {c['total_orders']}
Spent     : {fmt_money(c['total_spent'])}
Wallet    : {fmt_money(c.get('wallet', 0))}
Joined    : {fmt_date_short(c['joined_at'])}
Last Buy  : {fmt_date_short(c.get('last_purchase'))}
Notes     : {c.get('notes') or 'None'}
━━━━━━━━━━━━━━━━━━━━
*Recent Orders*
"""
    for s in sales[:5]:
        text += f"• `{s['order_id']}` {s['product_name'].title()} — {fmt_money(s['sell_price'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    await blacklist_customer(context.args[0])
    await update.message.reply_text(f"🚫 @{context.args[0].lstrip('@')} blacklisted!")

@admin_only
async def cmd_unblacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    await blacklist_customer(context.args[0], False)
    await update.message.reply_text(f"✅ @{context.args[0].lstrip('@')} removed from blacklist!")

@admin_only
async def cmd_setvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    await set_vip(context.args[0])
    await update.message.reply_text(f"👑 @{context.args[0].lstrip('@')} is now VIP!")

@admin_only
async def cmd_addnote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/addnote @user note text here`", parse_mode="Markdown")
        return
    note = " ".join(args[1:])
    await add_customer_note(args[0], note)
    await update.message.reply_text(f"📝 Note added for @{args[0].lstrip('@')}!")

@admin_only
async def cmd_addwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/addwallet @user amount`", parse_mode="Markdown")
        return
    await add_wallet_credit(args[0], float(args[1]))
    await update.message.reply_text(f"💰 {fmt_money(float(args[1]))} added to @{args[0].lstrip('@')}'s wallet!")

@admin_only
async def cmd_inactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    customers = await get_inactive_customers(30)
    if not customers:
        await update.message.reply_text("No inactive customers!")
        return
    text = "😴 *Inactive Customers (30+ days)*\n━━━━━━━━━━━━━━━━━━━━\n"
    for c in customers[:15]:
        text += f"• @{c['username']} | Last: {fmt_date_short(c.get('last_purchase'))}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── EXPENSES ────────────────────────────────────────────────
@admin_only
async def cmd_addexpense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/addexpense description amount [category]`\nExample: `/addexpense recharge 500 restock`", parse_mode="Markdown")
        return
    try:
        amount = float(args[-1])
        desc = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("❌ Amount must be a number!")
        return
    await log_expense(desc, amount)
    await update.message.reply_text(f"💸 Expense logged: *{desc}* — {fmt_money(amount)}", parse_mode="Markdown")

@admin_only
async def cmd_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    expenses = await get_expenses(start=today)
    total = await get_expenses_total(start=today)
    text = "💸 *Today's Expenses*\n━━━━━━━━━━━━━━━━━━━━\n"
    for e in expenses:
        text += f"• {e['description']} — {fmt_money(e['amount'])}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\nTotal: {fmt_money(total)}"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── DEBTS ───────────────────────────────────────────────────
@admin_only
async def cmd_adddebt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: `/adddebt @user amount product`", parse_mode="Markdown")
        return
    await add_debt(args[0], float(args[1]), args[2])
    await update.message.reply_text(f"📌 Debt recorded: @{args[0].lstrip('@')} owes {fmt_money(float(args[1]))} for {args[2].title()}")

@admin_only
async def cmd_debts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debts = await get_unpaid_debts()
    if not debts:
        await update.message.reply_text("✅ No unpaid debts!")
        return
    text = "📌 *Unpaid Debts*\n━━━━━━━━━━━━━━━━━━━━\n"
    for d in debts:
        text += f"• @{d['buyer_username']} | {d['product_name'].title()} | {fmt_money(d['amount'])} | {fmt_date_short(d['created_at'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── CREDENTIALS ─────────────────────────────────────────────
@admin_only
async def cmd_addcred(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: `/addcred product email password [expiry YYYY-MM-DD]`", parse_mode="Markdown")
        return
    product = args[0]
    email = args[1]
    password = args[2]
    expiry = None
    if len(args) > 3:
        try:
            expiry = tz.localize(datetime.strptime(args[3], "%Y-%m-%d"))
        except ValueError:
            pass
    await store_credentials(product, email, password, expiry)
    await update.message.reply_text(f"🔑 Credential added for *{product.title()}*!", parse_mode="Markdown")

@admin_only
async def cmd_credstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stock = await get_credentials_stock()
    if not stock:
        await update.message.reply_text("No credentials stored!")
        return
    text = "🔑 *Credential Stock*\n━━━━━━━━━━━━━━━━━━━━\n"
    for s in stock:
        text += f"• {s['_id'].title()}: {s['available']} available / {s['total']} total\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_expiringcreds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    creds = await get_expiring_credentials(3)
    if not creds:
        await update.message.reply_text("✅ No credentials expiring soon!")
        return
    text = "⚠️ *Expiring Credentials (3 days)*\n━━━━━━━━━━━━━━━━━━━━\n"
    for c in creds:
        text += f"• {c['product_name'].title()} | {c['email']} | Expires: {fmt_date_short(c.get('expiry'))} | @{c.get('assigned_to','?')}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── COUPONS ─────────────────────────────────────────────────
@admin_only
async def cmd_addcoupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: `/addcoupon CODE discount_percent [max_uses]`\nExample: `/addcoupon SAVE20 20 100`", parse_mode="Markdown")
        return
    code = args[0].upper()
    percent = float(args[1])
    max_uses = int(args[2]) if len(args) > 2 else None
    await add_coupon(code, percent, max_uses)
    await update.message.reply_text(f"🎟️ Coupon `{code}` created! {percent}% off{f', max {max_uses} uses' if max_uses else ''}", parse_mode="Markdown")

@admin_only
async def cmd_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coupons = await db.coupons.find({"active": True}).to_list(None)
    if not coupons:
        await update.message.reply_text("No active coupons!")
        return
    text = "🎟️ *Active Coupons*\n━━━━━━━━━━━━━━━━━━━━\n"
    for c in coupons:
        uses_info = f"{c['uses']}/{c['max_uses']}" if c.get("max_uses") else f"{c['uses']}/∞"
        text += f"• `{c['code']}` — {c['discount_percent']}% off | Uses: {uses_info}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── SUPPORT TICKETS ─────────────────────────────────────────
@admin_only
async def cmd_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickets = await get_open_tickets()
    if not tickets:
        await update.message.reply_text("✅ No open tickets!")
        return
    text = "🎫 *Open Support Tickets*\n━━━━━━━━━━━━━━━━━━━━\n"
    for t in tickets:
        text += f"• `{t['ticket_id']}` | @{t['username']} | {t['issue'][:40]}...\n"
    text += "\nUse `/closeticket TKTID` to resolve"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_closeticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/closeticket TKTID`", parse_mode="Markdown")
        return
    ticket_id = context.args[0].upper()
    ticket = await db.tickets.find_one({"ticket_id": ticket_id})
    await close_ticket(ticket_id)
    await update.message.reply_text(f"✅ Ticket `{ticket_id}` resolved!")
    if ticket:
        user = await db.users.find_one({"username": ticket["username"]})
        if user:
            try:
                await context.bot.send_message(user["user_id"], f"✅ Your support ticket `{ticket_id}` has been resolved!\nThank you for your patience.")
            except Exception:
                pass

# ─── BROADCAST ───────────────────────────────────────────────
@admin_only
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast Your message here`", parse_mode="Markdown")
        return
    message = " ".join(context.args)
    user_ids = await get_all_user_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, f"📢 *{BUSINESS_NAME}*\n\n{message}", parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"📢 Broadcast sent!\n✅ {sent} delivered | ❌ {failed} failed")

# ─── TOPSELLING & TOPCUSTOMERS ───────────────────────────────
@admin_only
async def cmd_topselling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = await get_best_selling_products(5)
    text = "🏆 *Top Selling Products*\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, p in enumerate(products, 1):
        text += f"{i}. *{p['_id'].title()}* — {p['count']} sold | {fmt_money(p['revenue'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cmd_topcustomers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    customers = await get_top_customers(10)
    text = "🏆 *Top Customers*\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, c in enumerate(customers, 1):
        vip = "👑" if c.get("vip") else ""
        text += f"{i}. @{c['username']} {vip} | {c['total_orders']} orders | {fmt_money(c['total_spent'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── EXPORT ──────────────────────────────────────────────────
@admin_only
async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Generating Excel report...")
    sales = await get_all_sales(limit=1000)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    headers = ["Order ID", "Buyer", "Product", "Sell Price", "Cost Price", "Profit", "Payment", "Status", "Date"]
    ws.append(headers)

    for s in sales:
        ws.append([
            s["order_id"], s["buyer_username"], s["product_name"].title(),
            s["sell_price"], s["cost_price"], s["profit"],
            s.get("payment_mode", ""), s["status"],
            fmt_date(s["created_at"])
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    await update.message.reply_document(
        document=buffer,
        filename=f"sales_export_{datetime.now(tz).strftime('%Y%m%d')}.xlsx",
        caption="📊 Sales Export Ready!"
    )

@admin_only
async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import BUSINESS_NAME, CURRENCY, TIMEZONE, LOW_STOCK_THRESHOLD, REPORT_TIME
    text = f"""
⚙️ *Bot Settings*
━━━━━━━━━━━━━━━━━━━━
🏪 Business  : {BUSINESS_NAME}
💱 Currency  : {CURRENCY}
🌏 Timezone  : {TIMEZONE}
📦 Low Stock : ≤{LOW_STOCK_THRESHOLD} units
📊 Report at : {REPORT_TIME}
👑 Admins    : {len(ADMIN_IDS)} admins
━━━━━━━━━━━━━━━━━━━━
Edit settings in your Railway environment variables.
"""
    await update.message.reply_text(text, parse_mode="Markdown")
