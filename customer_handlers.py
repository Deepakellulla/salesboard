from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
from database import *
from helpers import *
from config import ADMIN_IDS, BUSINESS_NAME, CURRENCY
from datetime import datetime
import pytz
from config import TIMEZONE

tz = pytz.timezone(TIMEZONE)

# Conversation states
TICKET_ISSUE = 1
COUPON_CODE = 2

# ─── START ───────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await register_user(user.id, user.username or str(user.id))

    keyboard = [
        [InlineKeyboardButton("🛍️ Products", callback_data="browse"),
         InlineKeyboardButton("📦 My Orders", callback_data="myorders")],
        [InlineKeyboardButton("📋 My Subscriptions", callback_data="mysubs"),
         InlineKeyboardButton("💳 My Profile", callback_data="myprofile")],
        [InlineKeyboardButton("🆘 Support", callback_data="support"),
         InlineKeyboardButton("🎟️ Use Coupon", callback_data="coupon")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Welcome to *{BUSINESS_NAME}*!\n\n"
        "We offer premium OTTs, software, and VPNs at the best prices.\n\n"
        "Use the menu below to get started 👇",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ─── MENU ────────────────────────────────────────────────────
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

# ─── BROWSE PRODUCTS ─────────────────────────────────────────
async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = await get_all_products()
    query = update.callback_query
    if query:
        await query.answer()

    if not products:
        msg = "😔 No products available right now. Check back soon!"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    # Group by category
    categories = {}
    for p in products:
        cat = p.get("category", "general").title()
        categories.setdefault(cat, []).append(p)

    text = f"🛍️ *{BUSINESS_NAME} — Product Catalog*\n━━━━━━━━━━━━━━━━━━━━\n"
    for cat, items in categories.items():
        text += f"\n📁 *{cat}*\n"
        for p in items:
            stock_icon = "🟢" if p["stock"] > 0 else "🔴"
            text += f"{stock_icon} *{p['display_name']}* — {fmt_money(p['sell_price'])}\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━\n💬 Contact admin to place an order!"

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="mainmenu")]]
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_products_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await browse_products(update, context)

# ─── MY ORDERS ───────────────────────────────────────────────
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    user = update.effective_user
    username = user.username or str(user.id)
    sales = await search_sales(buyer_username=username)

    if not sales:
        msg = "📦 You have no orders yet!"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    text = "📦 *Your Orders*\n━━━━━━━━━━━━━━━━━━━━\n"
    for s in sales[:10]:
        status_icon = "✅" if s["status"] == "delivered" else "🔄"
        refund = " 🔴" if s.get("refunded") else ""
        text += f"{status_icon} `{s['order_id']}` | {s['product_name'].title()} | {fmt_money(s['sell_price'])} | {fmt_date_short(s['created_at'])}{refund}\n"

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="mainmenu")]]
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_myorders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    sales = await search_sales(buyer_username=username)
    if not sales:
        await update.message.reply_text("📦 You have no orders yet!")
        return
    text = "📦 *Your Orders*\n━━━━━━━━━━━━━━━━━━━━\n"
    for s in sales[:10]:
        status_icon = "✅" if s["status"] == "delivered" else "🔄"
        text += f"{status_icon} `{s['order_id']}` | {s['product_name'].title()} | {fmt_money(s['sell_price'])} | {fmt_date_short(s['created_at'])}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── MY SUBSCRIPTIONS ────────────────────────────────────────
async def my_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    user = update.effective_user
    username = user.username or str(user.id)
    subs = await get_user_subscriptions(username)

    if not subs:
        msg = "📋 You have no active subscriptions tracked yet."
        if query:
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="mainmenu")]]))
        else:
            await update.message.reply_text(msg)
        return

    text = "📋 *Your Subscriptions*\n━━━━━━━━━━━━━━━━━━━━\n"
    now_dt = datetime.now(tz)
    for s in subs:
        expiry = s.get("expiry_date")
        if expiry:
            days_left = (expiry - now_dt).days
            if days_left < 0:
                icon = "🔴"
                days_str = "Expired!"
            elif days_left <= 3:
                icon = "⚠️"
                days_str = f"{days_left} days left"
            else:
                icon = "🟢"
                days_str = f"{days_left} days left"
        else:
            icon = "🟢"
            days_str = "N/A"
        text += f"{icon} *{s['product_name'].title()}* | Expires: {fmt_date_short(expiry)} ({days_str})\n"

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="mainmenu")]]
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_mysubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await my_subscriptions(update, context)

# ─── MY PROFILE ──────────────────────────────────────────────
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    user = update.effective_user
    username = user.username or str(user.id)
    c = await get_customer(username)

    if not c:
        msg = "👤 You haven't made any purchases yet. Browse our products to get started!"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    vip = "👑 VIP Member" if c.get("vip") else "🛍️ Customer"
    text = f"""
👤 *My Profile*
━━━━━━━━━━━━━━━━━━━━
Username  : @{c['username']}
Status    : {vip}
Orders    : {c['total_orders']}
Total Spent: {fmt_money(c['total_spent'])}
💰 Wallet  : {fmt_money(c.get('wallet', 0))}
Member Since: {fmt_date_short(c['joined_at'])}
Last Purchase: {fmt_date_short(c.get('last_purchase'))}
━━━━━━━━━━━━━━━━━━━━
"""
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="mainmenu")]]
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_myprofile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await my_profile(update, context)

# ─── SUPPORT TICKET ──────────────────────────────────────────
async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🆘 *Support Ticket*\n\nPlease describe your issue clearly and I'll pass it to the admin.\n\nType your issue below or /cancel to go back:",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🆘 *Support Ticket*\n\nPlease describe your issue clearly.\n\nType your issue below or /cancel to go back:",
            parse_mode="Markdown"
        )
    return TICKET_ISSUE

async def support_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    issue = update.message.text
    ticket_id = await create_ticket(user.id, username, issue)

    await update.message.reply_text(
        f"✅ Ticket `{ticket_id}` created!\nWe'll get back to you shortly.\n\n"
        f"Issue: _{issue[:100]}_",
        parse_mode="Markdown"
    )

    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🎫 *New Support Ticket!*\n\nTicket: `{ticket_id}`\nFrom: @{username}\nIssue: {issue}\n\nUse `/closeticket {ticket_id}` to resolve.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Use /menu to return to the main menu.")
    return ConversationHandler.END

async def cmd_mytickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    tickets = await get_user_tickets(username)
    if not tickets:
        await update.message.reply_text("🎫 You have no support tickets!")
        return
    text = "🎫 *Your Support Tickets*\n━━━━━━━━━━━━━━━━━━━━\n"
    for t in tickets:
        icon = "✅" if t["status"] == "resolved" else "🔄"
        text += f"{icon} `{t['ticket_id']}` | {t['issue'][:40]}... | {t['status'].title()}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── COUPON ──────────────────────────────────────────────────
async def coupon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🎟️ Enter your coupon code:")
    else:
        await update.message.reply_text("🎟️ Enter your coupon code:")
    return COUPON_CODE

async def coupon_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    coupon = await validate_coupon(code)
    if coupon:
        await update.message.reply_text(
            f"✅ Coupon *{code}* is valid!\n💰 You get *{coupon['discount_percent']}%* off your next purchase.\n\nShare this code with the admin when placing your order.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Invalid or expired coupon code!")
    return ConversationHandler.END

# ─── FAQ ─────────────────────────────────────────────────────
async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    text = f"""
❓ *Frequently Asked Questions*
━━━━━━━━━━━━━━━━━━━━

*Q: How do I place an order?*
A: Contact the admin directly on Telegram and tell them what you want to buy.

*Q: What payment methods do you accept?*
A: UPI, Cash, Crypto, Bank Transfer.

*Q: How fast is delivery?*
A: Usually within a few minutes after payment confirmation.

*Q: What if my credentials don't work?*
A: Use /support to raise a ticket and we'll fix it immediately.

*Q: Can I get a refund?*
A: Contact admin. Refunds are handled case by case.

*Q: How do I check my subscription expiry?*
A: Use /mysubs to see all your active subscriptions.

*Q: Do you have any offers?*
A: Use /products to see current pricing. Special offers are announced via broadcast.
━━━━━━━━━━━━━━━━━━━━
📞 Still have questions? Use /support
"""
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="mainmenu")]]
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_faq(update, context)

# ─── WALLET ──────────────────────────────────────────────────
async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    c = await get_customer(username)
    wallet = c.get("wallet", 0) if c else 0
    await update.message.reply_text(f"💰 *Your Wallet Balance:* {fmt_money(wallet)}", parse_mode="Markdown")

# ─── CALLBACK HANDLER ────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "browse":
        await browse_products(update, context)
    elif data == "myorders":
        await my_orders(update, context)
    elif data == "mysubs":
        await my_subscriptions(update, context)
    elif data == "myprofile":
        await my_profile(update, context)
    elif data == "faq":
        await show_faq(update, context)
    elif data == "mainmenu":
        keyboard = [
            [InlineKeyboardButton("🛍️ Products", callback_data="browse"),
             InlineKeyboardButton("📦 My Orders", callback_data="myorders")],
            [InlineKeyboardButton("📋 My Subscriptions", callback_data="mysubs"),
             InlineKeyboardButton("💳 My Profile", callback_data="myprofile")],
            [InlineKeyboardButton("🆘 Support", callback_data="support"),
             InlineKeyboardButton("🎟️ Use Coupon", callback_data="coupon")],
            [InlineKeyboardButton("❓ FAQ", callback_data="faq")]
        ]
        await query.edit_message_text(
            f"👋 Welcome to *{BUSINESS_NAME}*!\n\nUse the menu below 👇",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

# ─── SUPPORT CONVERSATION ────────────────────────────────────
support_conv = ConversationHandler(
    entry_points=[
        CommandHandler("support", support_start),
    ],
    states={
        TICKET_ISSUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_receive)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conv)],
)

coupon_conv = ConversationHandler(
    entry_points=[
        CommandHandler("coupon", coupon_start),
    ],
    states={
        COUPON_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, coupon_check)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conv)],
)
