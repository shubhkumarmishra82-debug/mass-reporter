# ------------------------------------------------
# Created by: Dileep
# Copyright © 2026
# ------------------------------------------------
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID, LOG_GROUP, FORCE_JOIN_BUTTON_TEXT
from database import Database
import asyncio

db = Database()


def is_owner(user_id: int) -> bool:
    """Check if the user is the bot owner."""
    return user_id == OWNER_ID


def build_force_join_buttons() -> InlineKeyboardMarkup:
    """Build force join inline keyboard buttons from database channels."""
    channels = db.get_all_channels()
    buttons = []
    row = []
    for i, ch in enumerate(channels):
        link = ch.get("invite_link") or (
            f"https://t.me/{ch['chat_username']}" if ch.get("chat_username") else None
        )
        if not link:
            continue
        row.append(InlineKeyboardButton(FORCE_JOIN_BUTTON_TEXT, url=link))
        if len(row) == 2 or i == len(channels) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("âœ… Verify", callback_data="verify")])
    return InlineKeyboardMarkup(buttons)


def build_panel_buttons() -> InlineKeyboardMarkup:
    """Build panel buttons after verification."""
    buttons = [
        [InlineKeyboardButton("ðŸ—³ Pannel", callback_data="panel"),
         InlineKeyboardButton("âŒ Close", callback_data="close")]
    ]
    return InlineKeyboardMarkup(buttons)


def build_account_menu_buttons() -> InlineKeyboardMarkup:
    """Build account management menu buttons."""
    buttons = [
        [InlineKeyboardButton("âš™ï¸ Account Setting", callback_data="add_account")],
        [InlineKeyboardButton("ðŸ“‹ My Account", callback_data="my_account")],
        [InlineKeyboardButton("âš¡ Start Attack", callback_data="start_attack")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(buttons)


def build_add_account_buttons() -> InlineKeyboardMarkup:
    """Build add account type selection buttons."""
    buttons = [
        [InlineKeyboardButton("ðŸ“± Mobile Number", callback_data="acc_phone")],
        [InlineKeyboardButton("ðŸ”— String Session", callback_data="acc_string")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="back_panel")]
    ]
    return InlineKeyboardMarkup(buttons)


def build_my_accounts_buttons(owner_id: int) -> InlineKeyboardMarkup:
    """Build buttons for all accounts of a user."""
    accounts = db.get_user_accounts(owner_id)
    buttons = []
    row = []
    for i, acc in enumerate(accounts):
        name = acc.get("first_name") or acc.get("phone") or "Unknown"
        btn = InlineKeyboardButton(f"ðŸ‘¤ {name}", callback_data=f"acc_{acc['_id']}")
        row.append(btn)
        if len(row) == 2 or i == len(accounts) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="back_panel")])
    return InlineKeyboardMarkup(buttons)


def build_account_detail_buttons(account_id) -> InlineKeyboardMarkup:
    """Build buttons for account detail view."""
    buttons = [
        [InlineKeyboardButton("ðŸ—‘ Remove Account", callback_data=f"rm_acc_{account_id}")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="my_account")]
    ]
    return InlineKeyboardMarkup(buttons)


def build_target_type_buttons() -> InlineKeyboardMarkup:
    """Build target type selection buttons."""
    buttons = [
        [InlineKeyboardButton("ðŸ‘¤ User Acc.", callback_data="target_user")],
        [InlineKeyboardButton("ðŸ“¢ Channel", callback_data="target_channel")],
        [InlineKeyboardButton("ðŸ‘¥ Group", callback_data="target_group")],
        [InlineKeyboardButton("ðŸ¤– Bot", callback_data="target_bot")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="back_panel")]
    ]
    return InlineKeyboardMarkup(buttons)


def build_group_type_buttons() -> InlineKeyboardMarkup:
    """Build group type selection buttons."""
    buttons = [
        [InlineKeyboardButton("ðŸ”’ Private Group", callback_data="grp_private")],
        [InlineKeyboardButton("ðŸŒ Public Group", callback_data="grp_public")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="target_group")]
    ]
    return InlineKeyboardMarkup(buttons)


def build_channel_type_buttons() -> InlineKeyboardMarkup:
    """Build channel type selection buttons."""
    buttons = [
        [InlineKeyboardButton("ðŸ”’ Private Channel", callback_data="ch_private")],
        [InlineKeyboardButton("ðŸŒ Public Channel", callback_data="ch_public")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="target_channel")]
    ]
    return InlineKeyboardMarkup(buttons)


def build_report_buttons() -> InlineKeyboardMarkup:
    """Build report category selection buttons."""
    from report_categories import get_top_level_buttons
    return get_top_level_buttons()


def build_channel_settings_buttons() -> InlineKeyboardMarkup:
    """Build channel settings buttons (placeholder)."""
    buttons = [
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="back_panel")]
    ]
    return InlineKeyboardMarkup(buttons)


async def send_log(client: Client, text: str, quote: bool = False):
    """Send a log message to the log group with optional quote styling."""
    try:
        if quote:
            # Wrap in a quote-style block
            lines = text.strip().split("\n")
            quoted_lines = []
            for line in lines:
                quoted_lines.append(f"â–Ž {line}")
            text = "\n".join(quoted_lines)
        await client.send_message(LOG_GROUP, text, disable_web_page_preview=True)
    except Exception as e:
        print(f"Log error: {e}")


async def check_session_valid(session_string: str) -> tuple:
    """Check if a string session is valid.
    Returns (valid: bool, user_info: dict or None)
    """
    from config import API_ID, API_HASH
    try:
        client = Client(
            f"check_session_{id(session_string)}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            no_updates=True
        )
        await client.start()
        me = await client.get_me()
        user_info = {
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "user_id": me.id
        }
        await client.stop()
        return True, user_info
    except Exception as e:
        print(f"Session check error: {e}")
        return False, None


def mention_user(user_id: int, name: str) -> str:
    """Create an HTML mention for a user."""
    safe_name = name.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'


async def resolve_target(client: Client, target_input: str) -> dict:
    """Resolve a target user from username or user ID.
    
    Handles:
    - @username format
    - Numeric user IDs
    - Plain usernames without @
    
    Returns dict with first_name, last_name, username, user_id or None on failure.
    """
    try:
        target_input = target_input.strip()
        
        # Try as username
        if target_input.startswith("@"):
            user = await client.get_users(target_input)
        # Try as numeric ID
        elif target_input.lstrip("-").isdigit():
            user = await client.get_users(int(target_input))
        # Try as plain username
        else:
            try:
                user = await client.get_users(target_input)
            except Exception:
                # Try with @ prefix
                user = await client.get_users(f"@{target_input}")

        if isinstance(user, list):
            user = user[0]

        return {
            "first_name": user.first_name or "None",
            "last_name": user.last_name or "",
            "username": user.username,
            "user_id": user.id
        }
    except Exception as e:
        print(f"Resolve target error: {e}")
        return None
