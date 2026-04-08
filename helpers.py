from config import CURRENCY, BUSINESS_NAME
from datetime import datetime
import pytz
from config import TIMEZONE

tz = pytz.timezone(TIMEZONE)

def fmt_money(amount):
    return f"{CURRENCY}{amount:,.2f}"

def fmt_date(dt):
    if not dt:
        return "N/A"
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    return dt.strftime("%d %b %Y %I:%M %p")

def fmt_date_short(dt):
    if not dt:
        return "N/A"
    return dt.strftime("%d %b %Y")

def sale_receipt(order_id, product, sell_price, profit, buyer, payment_mode, credentials=""):
    text = f"""
🧾 *RECEIPT — {BUSINESS_NAME}*
━━━━━━━━━━━━━━━━━━━━
📦 Order ID : `{order_id}`
🛍️ Product  : {product.title()}
👤 Buyer    : @{buyer}
💳 Payment  : {payment_mode.upper()}
💰 Amount   : {fmt_money(sell_price)}
📈 Profit   : {fmt_money(profit)}
📅 Date     : {fmt_date(datetime.now(tz))}
━━━━━━━━━━━━━━━━━━━━
"""
    if credentials:
        text += f"🔑 Credentials:\n`{credentials}`\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "✅ Delivered!"
    return text

def customer_receipt(order_id, product, sell_price, buyer, payment_mode, credentials=""):
    text = f"""
🧾 *ORDER CONFIRMED — {BUSINESS_NAME}*
━━━━━━━━━━━━━━━━━━━━
📦 Order ID : `{order_id}`
🛍️ Product  : {product.title()}
💳 Payment  : {payment_mode.upper()}
💰 Amount   : {fmt_money(sell_price)}
📅 Date     : {fmt_date(datetime.now(tz))}
━━━━━━━━━━━━━━━━━━━━
"""
    if credentials:
        text += f"🔑 Your Credentials:\n`{credentials}`\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "✅ Thank you for your purchase!\n💬 For support, use /support"
    return text

def stats_block(label, revenue, cost, profit, orders, expenses=0):
    net = profit - expenses
    return f"""
📊 *{label} Stats*
━━━━━━━━━━━━━━━━━━━━
📦 Orders      : {orders}
💵 Revenue     : {fmt_money(revenue)}
💸 Cost        : {fmt_money(cost)}
📈 Gross Profit: {fmt_money(profit)}
🧾 Expenses    : {fmt_money(expenses)}
💰 Net Profit  : {fmt_money(net)}
━━━━━━━━━━━━━━━━━━━━
"""

def is_admin(user_id, admin_ids):
    return user_id in admin_ids

PAYMENT_MODES = ["upi", "cash", "crypto", "bank", "wallet"]
DURATIONS = ["1 month", "3 months", "6 months", "1 year"]
