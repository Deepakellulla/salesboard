import asyncio
import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from config import BOT_TOKEN
from database import init_db
from admin_handlers import (
    admin_menu, cmd_sold, cmd_quicksold, cmd_orders, cmd_orderstatus,
    cmd_refund, cmd_search, cmd_addproduct, cmd_products, cmd_editstock,
    cmd_lowstock, cmd_deleteproduct, cmd_stats, cmd_statsweek,
    cmd_statsmonth, cmd_statsall, cmd_paymentmodes, cmd_customers,
    cmd_customer, cmd_blacklist, cmd_unblacklist, cmd_setvip, cmd_addnote,
    cmd_addwallet, cmd_inactive, cmd_addexpense, cmd_expenses, cmd_adddebt,
    cmd_debts, cmd_addcred, cmd_credstock, cmd_expiringcreds, cmd_addcoupon,
    cmd_coupons, cmd_tickets, cmd_closeticket, cmd_broadcast, cmd_topselling,
    cmd_topcustomers, cmd_export, cmd_settings
)
from customer_handlers import (
    cmd_start, cmd_menu, cmd_products_customer, cmd_myorders, cmd_mysubs,
    cmd_myprofile, cmd_mytickets, cmd_wallet, cmd_faq,
    button_callback, support_conv, coupon_conv
)
from scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ─── CUSTOMER COMMANDS ──────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("products", cmd_products_customer))
    app.add_handler(CommandHandler("myorders", cmd_myorders))
    app.add_handler(CommandHandler("mysubs", cmd_mysubs))
    app.add_handler(CommandHandler("myprofile", cmd_myprofile))
    app.add_handler(CommandHandler("mytickets", cmd_mytickets))
    app.add_handler(CommandHandler("wallet", cmd_wallet))
    app.add_handler(CommandHandler("faq", cmd_faq))
    app.add_handler(support_conv)
    app.add_handler(coupon_conv)

    # ─── ADMIN COMMANDS ─────────────────────────────────────
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(CommandHandler("sold", cmd_sold))
    app.add_handler(CommandHandler("quicksold", cmd_quicksold))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("orderstatus", cmd_orderstatus))
    app.add_handler(CommandHandler("refund", cmd_refund))
    app.add_handler(CommandHandler("search", cmd_search))

    app.add_handler(CommandHandler("addproduct", cmd_addproduct))
    app.add_handler(CommandHandler("editstock", cmd_editstock))
    app.add_handler(CommandHandler("lowstock", cmd_lowstock))
    app.add_handler(CommandHandler("deleteproduct", cmd_deleteproduct))

    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("statsweek", cmd_statsweek))
    app.add_handler(CommandHandler("statsmonth", cmd_statsmonth))
    app.add_handler(CommandHandler("statsall", cmd_statsall))
    app.add_handler(CommandHandler("paymentmodes", cmd_paymentmodes))

    app.add_handler(CommandHandler("customers", cmd_customers))
    app.add_handler(CommandHandler("customer", cmd_customer))
    app.add_handler(CommandHandler("blacklist", cmd_blacklist))
    app.add_handler(CommandHandler("unblacklist", cmd_unblacklist))
    app.add_handler(CommandHandler("setvip", cmd_setvip))
    app.add_handler(CommandHandler("addnote", cmd_addnote))
    app.add_handler(CommandHandler("addwallet", cmd_addwallet))
    app.add_handler(CommandHandler("inactive", cmd_inactive))

    app.add_handler(CommandHandler("addexpense", cmd_addexpense))
    app.add_handler(CommandHandler("expenses", cmd_expenses))
    app.add_handler(CommandHandler("adddebt", cmd_adddebt))
    app.add_handler(CommandHandler("debts", cmd_debts))

    app.add_handler(CommandHandler("addcred", cmd_addcred))
    app.add_handler(CommandHandler("credstock", cmd_credstock))
    app.add_handler(CommandHandler("expiringcreds", cmd_expiringcreds))

    app.add_handler(CommandHandler("addcoupon", cmd_addcoupon))
    app.add_handler(CommandHandler("coupons", cmd_coupons))

    app.add_handler(CommandHandler("tickets", cmd_tickets))
    app.add_handler(CommandHandler("closeticket", cmd_closeticket))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("topselling", cmd_topselling))
    app.add_handler(CommandHandler("topcustomers", cmd_topcustomers))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("settings", cmd_settings))

    # Admin products list (override customer one for admins)
    app.add_handler(CommandHandler("allproducts", cmd_products))

    # ─── CALLBACK QUERY ─────────────────────────────────────
    app.add_handler(CallbackQueryHandler(button_callback))

    # ─── POST INIT (DB + Scheduler) ─────────────────────────
    async def post_init(application):
        await init_db()
        setup_scheduler(application.bot)
        logger.info("🚀 Bot is running!")

    app.post_init = post_init

    logger.info("Starting bot...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
