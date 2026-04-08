from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import *
from helpers import *
from config import ADMIN_IDS, REPORT_TIME, LOW_STOCK_THRESHOLD, TIMEZONE
from datetime import datetime, timedelta
import pytz

tz = pytz.timezone(TIMEZONE)
scheduler = AsyncIOScheduler(timezone=tz)

def setup_scheduler(bot):

    # ─── DAILY REPORT ──────────────────────────────────────────
    hour, minute = REPORT_TIME.split(":")

    @scheduler.scheduled_job(CronTrigger(hour=int(hour), minute=int(minute), timezone=tz))
    async def daily_report():
        today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        s = await get_sales_stats(start=today)
        e = await get_expenses_total(start=today)
        best = await get_best_selling_products(3, start=today)

        top_products = ""
        for p in best:
            top_products += f"  • {p['_id'].title()}: {p['count']} sold\n"

        report = f"""
📊 *Daily Report — {datetime.now(tz).strftime('%d %b %Y')}*
━━━━━━━━━━━━━━━━━━━━
📦 Orders     : {s['total_orders']}
💵 Revenue    : {fmt_money(s['total_revenue'])}
💸 Cost       : {fmt_money(s['total_cost'])}
📈 Gross Profit: {fmt_money(s['total_profit'])}
🧾 Expenses   : {fmt_money(e)}
💰 Net Profit : {fmt_money(s['total_profit'] - e)}
━━━━━━━━━━━━━━━━━━━━
🏆 Top Products Today:
{top_products or '  No sales yet'}━━━━━━━━━━━━━━━━━━━━
"""
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, report, parse_mode="Markdown")
            except Exception:
                pass

    # ─── LOW STOCK ALERT ───────────────────────────────────────
    @scheduler.scheduled_job(CronTrigger(hour=10, minute=0, timezone=tz))
    async def low_stock_check():
        items = await get_low_stock_products(LOW_STOCK_THRESHOLD)
        if items:
            text = f"⚠️ *Low Stock Alert!*\n━━━━━━━━━━━━━━━━━━━━\n"
            for p in items:
                text += f"🔴 {p['display_name']} — only {p['stock']} left!\n"
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, text, parse_mode="Markdown")
                except Exception:
                    pass

    # ─── EXPIRY REMINDERS ──────────────────────────────────────
    @scheduler.scheduled_job(CronTrigger(hour=9, minute=0, timezone=tz))
    async def expiry_reminders():
        subs = await get_expiring_subscriptions(days=3)
        for sub in subs:
            user = await db.users.find_one({"username": sub["username"]})
            if user:
                days_left = (sub["expiry_date"] - datetime.now(tz)).days
                try:
                    await bot.send_message(
                        user["user_id"],
                        f"⚠️ *Subscription Expiry Reminder!*\n\n"
                        f"Your *{sub['product_name'].title()}* subscription expires in *{days_left} day(s)*!\n\n"
                        f"Contact admin to renew and keep enjoying uninterrupted service. 🙏",
                        parse_mode="Markdown"
                    )
                    await mark_reminded(str(sub["_id"]))
                except Exception:
                    pass

            # Also notify admin
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"🔔 *Renewal Alert*\n@{sub['username']}'s {sub['product_name'].title()} expires in {(sub['expiry_date'] - datetime.now(tz)).days} days!\nOrder: `{sub.get('order_id', 'N/A')}`",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

    # ─── EXPIRING CREDENTIALS ALERT ────────────────────────────
    @scheduler.scheduled_job(CronTrigger(hour=8, minute=0, timezone=tz))
    async def cred_expiry_check():
        creds = await get_expiring_credentials(days=3)
        if creds:
            text = "🔑 *Credentials Expiring Soon!*\n━━━━━━━━━━━━━━━━━━━━\n"
            for c in creds:
                days = (c["expiry"] - datetime.now(tz)).days
                text += f"• {c['product_name'].title()} | {c['email']} | {days}d left | @{c.get('assigned_to', '?')}\n"
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, text, parse_mode="Markdown")
                except Exception:
                    pass

    # ─── DEBT REMINDER ─────────────────────────────────────────
    @scheduler.scheduled_job(CronTrigger(day_of_week="mon", hour=10, minute=0, timezone=tz))
    async def debt_reminder():
        debts = await get_unpaid_debts()
        if debts:
            text = f"📌 *Weekly Debt Reminder*\n━━━━━━━━━━━━━━━━━━━━\n"
            total = 0
            for d in debts:
                text += f"• @{d['buyer_username']} | {d['product_name'].title()} | {fmt_money(d['amount'])}\n"
                total += d["amount"]
            text += f"━━━━━━━━━━━━━━━━━━━━\nTotal Owed: {fmt_money(total)}"
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, text, parse_mode="Markdown")
                except Exception:
                    pass

    scheduler.start()
    print("✅ Scheduler started.")
