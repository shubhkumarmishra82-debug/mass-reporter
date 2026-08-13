# ⚔️ Mass Reporter Bot

A powerful Telegram Mass Reporting Bot with force join system, multi-account management, and automated reporting capabilities.

## ✨ Features

### 🔐 Force Join System
- Add channels/groups for mandatory join before bot usage
- Support for **Normal Mode** (direct join link) and **Request Mode** (join request link)
- Auto-verification system to check if users have joined all required channels
- Real-time logging when users join/request to join

### 👤 Account Management
- Add Telegram accounts via **Mobile Number** (with OTP verification)
- Add Telegram accounts via **Telethon String Session**
- View, manage, and remove added accounts
- Account status tracking (active/inactive)

### ⚡ Mass Reporting
- **User Account Reporting** - Report any Telegram user
- **Channel Reporting** - Report channels (private & public)
- **Group Reporting** - Report groups (private & public)
- **Bot Reporting** - Report Telegram bots
- Multi-account reporting - Each account reports the target
- Configurable report count per account
- 5-second delay between reports to avoid FloodWait

### 📝 Report Categories
- 🙅 I Don't Like It
- 🧒 Child Abuse (Sexual / Physical)
- ⚔️ Violence (8 subcategories)
- 💼 Illegal Goods & Services (6 subcategories with deeper nesting)
- 📨 Spam
- 🔞 Pornography
- ©️ Copyright Violation
- 📋 Personal Data Leak
- 🎭 Fake Account

### 📊 Logging
- All activities logged to a designated log group
- Quote-styled log messages
- User mentions and detailed info in logs

## 🚀 Deployment

### Prerequisites
- Python 3.11+
- MongoDB database
- Telegram API credentials (API_ID & API_HASH)
- Telegram Bot Token (from @BotFather)
- A Telegram Group for logs

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/mass-reporter-bot.git
cd mass-reporter-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_ID=your_telegram_user_id
LOG_GROUP=your_log_group_id
MONGO_URI=mongodb://localhost:27017
DB_NAME=mass_reporter
```

### 4. Run the Bot
```bash
python3 bot.py
```

## 📋 Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Start the bot | All Users |
| `/add_channel` | Add a channel for force join | Owner Only |
| `/rm_channel` | Remove a channel from force join | Owner Only |
| `/c_list` | List all force join channels | Owner Only |

## 🔄 Bot Flow

### For Users:
1. **Start** → Force join channels displayed
2. **Verify** → After joining all channels, click Verify
3. **Panel** → Access account management & attack features
4. **Add Account** → Add via phone number or string session
5. **Start Attack** → Select target type → Choose report reason → Set count → Attack starts

### For Owner:
1. **`/add_channel`** → Forward a message or send a link from the channel
2. Bot checks admin status with animation
3. Select **Normal Mode** or **Request Mode**
4. Invite link is created automatically
5. **`/rm_channel`** → Send channel ID to remove
6. **`/c_list`** → View all force join channels

## 🛡️ Account Addition Methods

### Mobile Number Method:
1. Click "📱 Mobile Number"
2. Send phone number in `+918472927177` format
3. Bot sends OTP to the Telegram account
4. Send the OTP received
5. Send the 2FA password (if enabled)
6. Account is added automatically

### String Session Method:
1. Click "🔗 String Session"
2. Send a valid Telethon/Pyrogram string session
3. Bot validates the session
4. If valid, account is added automatically

## 📁 Project Structure

```
mass-reporter-bot/
├── bot.py                 # Main bot file with all handlers
├── config.py              # Configuration & environment variables
├── database.py            # MongoDB database operations
├── helpers.py             # Utility functions & button builders
├── report_categories.py   # Report reason tree & categories
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── Procfile               # For Heroku deployment
├── runtime.txt            # Python version for deployment
└── README.md              # This file
```

## 🗄️ Database Collections (MongoDB)

### Users Collection
```json
{
  "user_id": 123456789,
  "first_name": "User",
  "username": "username",
  "verified": false,
  "accounts": [],
  "joined_at": 1234567890.0
}
```

### Channels Collection
```json
{
  "chat_id": -1001234567890,
  "chat_title": "Channel Name",
  "chat_username": "channel_username",
  "invite_link": "https://t.me/+xxxxx",
  "mode": "normal",
  "added_at": 1234567890.0
}
```

### Accounts Collection
```json
{
  "owner_id": 123456789,
  "phone": "+918472927177",
  "session_string": "session_string_here",
  "first_name": "Account Name",
  "username": "account_username",
  "user_id": 987654321,
  "account_type": "phone",
  "active": true,
  "added_at": 1234567890.0
}
```

## ☁️ Deploy to Heroku

1. Create a new Heroku app
2. Add mLab MongoDB addon (or use external MongoDB)
3. Set all environment variables in Config Vars
4. Push the code to Heroku

```bash
heroku create
git push heroku main
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set OWNER_ID=your_owner_id
heroku config:set LOG_GROUP=your_log_group_id
heroku config:set MONGO_URI=your_mongodb_uri
```

## ☁️ Deploy to VPS

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run with screen
screen -S bot
python3 bot.py

# Or run with systemd (create a service file)
```

## ⚠️ Disclaimer

This bot is created for educational purposes only. Misuse of this bot may violate Telegram's Terms of Service. The developer is not responsible for any misuse or damage caused by this bot. Use at your own risk.

## 📝 License

This project is licensed under the MIT License.
