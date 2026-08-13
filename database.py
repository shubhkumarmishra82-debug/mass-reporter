# ------------------------------------------------
# Created by: Dileep
# Copyright © 2026
# ------------------------------------------------
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, COL_USERS, COL_CHANNELS, COL_ACCOUNTS
import time


class Database:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.users = self.db[COL_USERS]
        self.channels = self.db[COL_CHANNELS]
        self.accounts = self.db[COL_ACCOUNTS]

    # ==================== USER OPERATIONS ====================

    def add_user(self, user_id: int, first_name: str, username: str = None):
        """Add or update a user in the database."""
        existing = self.users.find_one({"user_id": user_id})
        if existing:
            self.users.update_one(
                {"user_id": user_id},
                {"$set": {"first_name": first_name, "username": username}}
            )
        else:
            self.users.insert_one({
                "user_id": user_id,
                "first_name": first_name,
                "username": username,
                "verified": False,
                "accounts": [],
                "joined_at": time.time()
            })

    def get_user(self, user_id: int):
        """Get a user from the database."""
        return self.users.find_one({"user_id": user_id})

    def is_verified(self, user_id: int) -> bool:
        """Check if a user is verified (completed force join)."""
        user = self.users.find_one({"user_id": user_id})
        return user.get("verified", False) if user else False

    def verify_user(self, user_id: int):
        """Mark a user as verified."""
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"verified": True}}
        )

    def unverify_user(self, user_id: int):
        """Mark a user as not verified."""
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"verified": False}}
        )

    # ==================== CHANNEL / FORCE JOIN OPERATIONS ====================

    def add_channel(self, chat_id: int, chat_title: str, chat_username: str = None,
                    invite_link: str = None, mode: str = "normal"):
        """Add a channel/group for force join."""
        existing = self.channels.find_one({"chat_id": chat_id})
        if existing:
            self.channels.update_one(
                {"chat_id": chat_id},
                {"$set": {
                    "chat_title": chat_title,
                    "chat_username": chat_username,
                    "invite_link": invite_link,
                    "mode": mode
                }}
            )
        else:
            self.channels.insert_one({
                "chat_id": chat_id,
                "chat_title": chat_title,
                "chat_username": chat_username,
                "invite_link": invite_link,
                "mode": mode,
                "added_at": time.time()
            })

    def remove_channel(self, chat_id: int):
        """Remove a channel/group from force join."""
        self.channels.delete_one({"chat_id": chat_id})

    def get_channel(self, chat_id: int):
        """Get a specific channel by chat_id."""
        return self.channels.find_one({"chat_id": chat_id})

    def get_all_channels(self):
        """Get all channels added for force join."""
        return list(self.channels.find({}))

    def update_channel_link(self, chat_id: int, invite_link: str):
        """Update the invite link for a channel."""
        self.channels.update_one(
            {"chat_id": chat_id},
            {"$set": {"invite_link": invite_link}}
        )

    def update_channel_mode(self, chat_id: int, mode: str):
        """Update the mode (normal/request) for a channel."""
        self.channels.update_one(
            {"chat_id": chat_id},
            {"$set": {"mode": mode}}
        )

    # ==================== ACCOUNT OPERATIONS ====================

    def add_account(self, owner_id: int, phone: str = None, session_string: str = None,
                    first_name: str = None, username: str = None, user_id: int = None,
                    account_type: str = "phone"):
        """Add a Telegram account for a user."""
        account_data = {
            "owner_id": owner_id,
            "phone": phone,
            "session_string": session_string,
            "first_name": first_name,
            "username": username,
            "user_id": user_id,
            "account_type": account_type,
            "active": True,
            "added_at": time.time()
        }
        result = self.accounts.insert_one(account_data)
        # Also add to user's accounts list
        self.users.update_one(
            {"user_id": owner_id},
            {"$push": {"accounts": result.inserted_id}}
        )
        return result.inserted_id

    def remove_account(self, account_id, owner_id: int):
        """Remove a Telegram account."""
        self.accounts.delete_one({"_id": account_id, "owner_id": owner_id})
        self.users.update_one(
            {"user_id": owner_id},
            {"$pull": {"accounts": account_id}}
        )

    def get_user_accounts(self, owner_id: int):
        """Get all accounts added by a user."""
        return list(self.accounts.find({"owner_id": owner_id, "active": True}))

    def get_account(self, account_id):
        """Get a specific account."""
        return self.accounts.find_one({"_id": account_id})

    def get_account_count(self, owner_id: int) -> int:
        """Get count of active accounts for a user."""
        return self.accounts.count_documents({"owner_id": owner_id, "active": True})

    def deactivate_account(self, account_id):
        """Deactivate an account."""
        self.accounts.update_one(
            {"_id": account_id},
            {"$set": {"active": False}}
        )

    # ==================== UTILITY ====================

    def get_all_users_count(self) -> int:
        """Get total number of users."""
        return self.users.count_documents({})

    def get_all_accounts_count(self) -> int:
        """Get total number of active accounts."""
        return self.accounts.count_documents({"active": True})
