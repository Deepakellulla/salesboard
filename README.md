# 🤖 Telegram Sales Bot

A full-featured Telegram bot for managing OTT, software, and VPN sales with MongoDB.

---

## 📁 File Structure

```
telegram-sales-bot/
├── main.py              # Entry point
├── config.py            # Configuration loader
├── database.py          # All MongoDB operations
├── helpers.py           # Utility functions
├── admin_handlers.py    # All admin commands
├── customer_handlers.py # Customer-facing commands
├── scheduler.py         # Automated daily tasks
├── requirements.txt     # Python dependencies
├── Procfile             # Railway process file
├── railway.json         # Railway config
└── .env.example         # Environment variables template
```

---

## 🚀 Setup Guide

### Step 1 — Create Your Telegram Bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy your **BOT_TOKEN**

### Step 2 — Get Your MongoDB URI
1. Go to [mongodb.com](https://mongodb.com) → Create free account
2. Create a new cluster (free tier is fine)
3. Go to **Connect** → **Drivers** → Copy the connection string
4. Replace `<password>` with your actual password

### Step 3 — Get Your Telegram User ID
1. Search for **@userinfobot** on Telegram
2. Send any message to get your **user ID**
3. This is your `ADMIN_IDS`

### Step 4 — Deploy on Railway

#### Method A: GitHub (Recommended)
1. Push this code to a GitHub repository
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repository
4. Go to **Variables** tab and add all env variables (see below)
5. Railway auto-deploys!

#### Method B: Railway CLI
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Step 5 — Set Environment Variables on Railway

Go to your Railway project → **Variables** tab → Add these:

| Variable | Value | Example |
|---|---|---|
| `BOT_TOKEN` | Your bot token from BotFather | `123456:ABC-DEF...` |
| `MONGODB_URI` | Your MongoDB connection string | `mongodb+srv://user:pass@cluster...` |
| `ADMIN_IDS` | Your Telegram user ID | `123456789` |
| `BUSINESS_NAME` | Your store name | `MyOTT Store` |
| `CURRENCY` | Currency symbol | `₹` |
| `TIMEZONE` | Your timezone | `Asia/Kolkata` |
| `LOW_STOCK_THRESHOLD` | Alert when stock ≤ this | `3` |
| `REPORT_TIME` | Daily report time (24h) | `21:00` |

---

## 👑 Admin Commands

### Sales
| Command | Description |
|---|---|
| `/sold @user product price cost` | Log a complete sale |
| `/quicksold product price cost` | Quick sale without buyer |
| `/orders` | View recent 10 orders |
| `/orderstatus ORDID status` | Update order status |
| `/refund ORDID` | Refund an order |
| `/search @user or ORDID` | Search orders |

### Products
| Command | Description |
|---|---|
| `/addproduct name cost sell stock cat` | Add product |
| `/allproducts` | View all products |
| `/editstock product +/-qty` | Update stock |
| `/lowstock` | View low stock items |
| `/deleteproduct name` | Remove product |

### Finance
| Command | Description |
|---|---|
| `/stats` | Today's stats |
| `/statsweek` | Last 7 days |
| `/statsmonth` | Last 30 days |
| `/statsall` | All time stats |
| `/addexpense desc amount` | Log expense |
| `/expenses` | Today's expenses |
| `/adddebt @user amount product` | Log a debt |
| `/debts` | View all unpaid debts |
| `/paymentmodes` | Payment breakdown |

### Customers
| Command | Description |
|---|---|
| `/customers` | Top 10 customers |
| `/customer @username` | Customer profile |
| `/blacklist @username` | Blacklist customer |
| `/setvip @username` | Set VIP status |
| `/addnote @user note` | Add private note |
| `/addwallet @user amount` | Add wallet credit |
| `/inactive` | Inactive customers |

### Credentials
| Command | Description |
|---|---|
| `/addcred product email pass expiry` | Store credentials |
| `/credstock` | View credential stock |
| `/expiringcreds` | Expiring in 3 days |

### Coupons
| Command | Description |
|---|---|
| `/addcoupon CODE percent maxuses` | Create coupon |
| `/coupons` | View all coupons |

### Reports
| Command | Description |
|---|---|
| `/export` | Download Excel file |
| `/topselling` | Best selling products |
| `/topcustomers` | Top buyers |
| `/broadcast message` | Message all users |
| `/tickets` | Open support tickets |
| `/closeticket TKTID` | Resolve a ticket |

---

## 👤 Customer Commands

| Command | Description |
|---|---|
| `/start` | Welcome menu |
| `/menu` | Main menu |
| `/products` | Browse products |
| `/myorders` | My order history |
| `/mysubs` | My subscriptions |
| `/myprofile` | My profile & stats |
| `/wallet` | Wallet balance |
| `/support` | Raise a support ticket |
| `/mytickets` | View my tickets |
| `/coupon` | Check a coupon code |
| `/faq` | Frequently asked questions |

---

## ⏰ Automated Tasks (Scheduler)

| Task | Time |
|---|---|
| Daily profit report | Your set `REPORT_TIME` |
| Low stock check | 10:00 AM daily |
| Subscription expiry reminders | 9:00 AM daily |
| Credential expiry alerts | 8:00 AM daily |
| Weekly debt reminder | Monday 10:00 AM |

---

## 💡 Quick Start After Deploy

1. Start your bot: `/start`
2. Open admin panel: `/admin`
3. Add your first product: `/addproduct Netflix 70 149 5 ott`
4. Log your first sale: `/sold @customer netflix 149 70 upi`
5. Check today's stats: `/stats`

---

## 🔧 Tips

- Multiple admins: Add comma-separated IDs in `ADMIN_IDS` (e.g., `123,456,789`)
- To add subscription tracker with a sale, use `/addcred` and then link in the order notes
- Export your data weekly with `/export` as a backup
- Use `/broadcast` sparingly to avoid spamming customers
