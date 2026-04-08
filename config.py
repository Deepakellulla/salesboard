import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "My Digital Store")
CURRENCY = os.getenv("CURRENCY", "₹")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", "3"))
REPORT_TIME = os.getenv("REPORT_TIME", "21:00")
