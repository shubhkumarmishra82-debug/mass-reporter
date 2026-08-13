# ------------------------------------------------
# Created by: Dileep
# Copyright © 2026
# ------------------------------------------------
import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
LOG_GROUP = int(os.getenv("LOG_GROUP", "0"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mass_reporter")

# Report Settings
REPORT_DELAY = 5  # seconds between each report
MAX_ACCOUNTS_PER_USER = 50

# Database Collection Names
COL_USERS = "users"
COL_CHANNELS = "channels"
COL_ACCOUNTS = "accounts"
COL_SESSIONS = "sessions"

# Bot Messages
WELCOME_IMAGE_URL = "https://telegra.ph/file/placeholder.jpg"

# Force Join Button Text
FORCE_JOIN_BUTTON_TEXT = "CLICK HEREðŸ”°"
