# ------------------------------------------------
# Created by: Dileep
# Copyright © 2026
# ------------------------------------------------
"""
Mass Reporter Bot - A Powerful Telegram Mass Reporting Bot
Features: Force Join, Multi-Account Management, Mass Reporting
Database: MongoDB
"""

import os
import asyncio
import re
import time
from bson import ObjectId
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message, InlineQueryResultArticle,
    InputTextMessageContent
)
from pyrogram.errors import (
    UserNotParticipant, ChatAdminRequired, FloodWait,
    UserDeactivated, SessionRevoked, AuthKeyUnregistered,
    PhoneNumberInvalid, PhoneCodeInvalid, PasswordHashInvalid,
    PeerIdInvalid, UsernameNotOccupied, ChannelPrivate,
    ChannelInvalid, InviteHashExpired, PhoneNumberBanned,
    ChatAdminRequired as ChatAdminErr
)

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, LOG_GROUP, REPORT_DELAY
from database import Database
from helpers import (
    is_owner, build_force_join_buttons, build_panel_buttons,
    build_account_menu_buttons, build_add_account_buttons,
    build_my_accounts_buttons, build_account_detail_buttons,
    build_target_type_buttons, build_group_type_buttons,
    build_channel_type_buttons, build_report_buttons,
    send_log, check_session_valid, mention_user, resolve_target,
    build_channel_settings_buttons
)
from report_categories import get_report_reason, get_subcategory_buttons

# Initialize Database
db = Database()

# ============ STATE TRACKING ============
# Conversation steps: {user_id: step_name}
user_steps = {}

# Temporary data: {user_id: dict}
temp_data = {}

# Phone sign-in flow: {user_id: {phone, phone_code_hash, session_string, otp}}
phone_flow = {}

# Report flow: {user_id: {target, reason, message, count, target_type}}
report_flow = {}

# ============ BOT CLIENT ============
app = Client(
    "mass_reporter_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# =====================================================================
#                      OWNER COMMANDS
# =====================================================================

@app.on_message(filters.command("add_channel") & filters.private)
async def add_channel_cmd(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    await message.reply_text(
        "ðŸ“¥ **Forward me any message from your channel or group**\n\n"
        "Or send me a message link from the channel/group.",
        parse_mode="markdown"
    )
    user_steps[message.from_user.id] = "add_channel_forward"


@app.on_message(filters.command("rm_channel") & filters.private)
async def rm_channel_cmd(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    await message.reply_text(
        "ðŸ“¤ **Send me the channel or group ID to remove from force join:**",
        parse_mode="markdown"
    )
    user_steps[message.from_user.id] = "rm_channel_id"


@app.on_message(filters.command("c_list") & filters.private)
async def channel_list_cmd(client: Client, message: Message):
    if not is_owner(message.from_user.id):
        return
    channels = db.get_all_channels()
    if not channels:
        await message.reply_text("âŒ No channels added for force join yet.")
        return
    text = "ðŸ“‹ **Force Join Channels/Groups:**\n\n"
    for i, ch in enumerate(channels, 1):
        mode_emoji = "ðŸ”—" if ch.get("mode") == "request" else "ðŸŒ"
        text += f"**{i}.** {ch['chat_title']}\n"
        text += f"   ID: `{ch['chat_id']}`\n"
        text += f"   Mode: {mode_emoji} {ch.get('mode', 'normal').title()}\n\n"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("âŒ Close", callback_data="close")]])
    await message.reply_text(text, parse_mode="markdown", reply_markup=buttons)


# =====================================================================
#                      FORWARD / LINK HANDLER FOR ADD_CHANNEL
# =====================================================================

@app.on_message(filters.private & filters.forwarded)
async def handle_forwarded(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    step = user_steps.get(user_id)
    if step != "add_channel_forward":
        return

    if not message.forward_from_chat:
        await message.reply_text("âŒ Could not detect the source. Please forward a message from a channel or group.")
        return

    chat = message.forward_from_chat
    chat_id = chat.id
    chat_title = chat.title or "Unknown"
    chat_username = chat.username

    # Animated checking status
    status_msg = await message.reply_text("ðŸ” Checking admin status")
    for i in range(3):
        dots = "â—" * (i + 1) + "â—‹" * (2 - i)
        await asyncio.sleep(0.6)
        await status_msg.edit_text(f"ðŸ” Checking admin status {dots}")

    # Check bot admin status
    try:
        member = await client.get_chat_member(chat_id, "me")
        is_admin = member.status in ["creator", "administrator"]
    except Exception:
        is_admin = False

    await status_msg.delete()

    if not is_admin:
        await message.reply_text("âŒ I am not an admin in that chat. Please make me admin first.")
        user_steps.pop(user_id, None)
        return

    # Store temporarily
    temp_data[user_id] = {
        "chat_id": chat_id,
        "chat_title": chat_title,
        "chat_username": chat_username
    }

    text = f"ðŸ“¢ **{chat_title}**\nðŸ†” `{chat_id}`\n\nSelect the invite link mode:"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("ðŸŒ Normal Mode", callback_data="mode_normal"),
         InlineKeyboardButton("ðŸ”— Request Mode", callback_data="mode_request")]
    ])
    await message.reply_text(text, parse_mode="markdown", reply_markup=buttons)
    user_steps.pop(user_id, None)


@app.on_message(filters.private & filters.regex(r"https?://t\.me/"))
async def handle_message_link(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    step = user_steps.get(user_id)
    if step != "add_channel_forward":
        return

    link = message.text.strip()

    # Animated checking
    status_msg = await message.reply_text("ðŸ” Checking admin status")
    for i in range(3):
        dots = "â—" * (i + 1) + "â—‹" * (2 - i)
        await asyncio.sleep(0.6)
        await status_msg.edit_text(f"ðŸ” Checking admin status {dots}")

    try:
        # Parse link patterns
        # https://t.me/c/1234567890/1 (private)
        # https://t.me/channelusername/1 (public)
        # https://t.me/+AbCdEfGh (invite link)
        chat = None
        
        if "/+/" in link or "/joinchat/" in link:
            # Invite link - try to join and get info
            try:
                chat = await client.get_chat(link)
            except Exception:
                pass
        elif "/c/" in link:
            match = re.match(r"https?://t\.me/c/(\d+)/\d+", link)
            if match:
                raw_id = int(match.group(1))
                chat_id_full = int(f"-100{raw_id}")
                chat = await client.get_chat(chat_id_full)
        else:
            match = re.match(r"https?://t\.me/([a-zA-Z0-9_]+)", link)
            if match:
                username = match.group(1)
                chat = await client.get_chat(username)

        if not chat:
            await status_msg.edit_text("âŒ Could not resolve the link. Make sure the bot is in that chat.")
            user_steps.pop(user_id, None)
            return

        chat_id = chat.id
        chat_title = chat.title or "Unknown"
        chat_username = chat.username

        # Check admin
        try:
            member = await client.get_chat_member(chat_id, "me")
            is_admin = member.status in ["creator", "administrator"]
        except Exception:
            is_admin = False

        await status_msg.delete()

        if not is_admin:
            await message.reply_text("âŒ I am not an admin in that chat. Please make me admin first.")
            user_steps.pop(user_id, None)
            return

        temp_data[user_id] = {
            "chat_id": chat_id,
            "chat_title": chat_title,
            "chat_username": chat_username
        }

        text = f"ðŸ“¢ **{chat_title}**\nðŸ†” `{chat_id}`\n\nSelect the invite link mode:"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("ðŸŒ Normal Mode", callback_data="mode_normal"),
             InlineKeyboardButton("ðŸ”— Request Mode", callback_data="mode_request")]
        ])
        await message.reply_text(text, parse_mode="markdown", reply_markup=buttons)
        user_steps.pop(user_id, None)

    except Exception as e:
        await status_msg.edit_text(f"âŒ Error: {str(e)}")
        user_steps.pop(user_id, None)


# =====================================================================
#                      TEXT INPUT HANDLER
# =====================================================================

@app.on_message(filters.private & ~filters.command(["start", "add_channel", "rm_channel", "c_list"]) & ~filters.forwarded & ~filters.regex(r"^/"))
async def handle_text_input(client: Client, message: Message):
    user_id = message.from_user.id
    step = user_steps.get(user_id)

    # ---------- REMOVE CHANNEL ----------
    if step == "rm_channel_id" and is_owner(user_id):
        try:
            chat_id = int(message.text.strip())
            ch = db.get_channel(chat_id)
            if ch:
                db.remove_channel(chat_id)
                await message.reply_text(
                    f"âœ… **{ch['chat_title']}** has been removed from force join.",
                    parse_mode="markdown"
                )
            else:
                await message.reply_text("âŒ Channel/Group not found in force join list.")
        except ValueError:
            await message.reply_text("âŒ Please send a valid numeric chat ID.")
        user_steps.pop(user_id, None)

    # ---------- PHONE NUMBER INPUT ----------
    elif step == "send_phone_number":
        phone = message.text.strip()
        if not phone.startswith("+"):
            await message.reply_text(
                "âŒ Please send phone number in **+918472927177** format.",
                parse_mode="markdown"
            )
            return

        status_msg = await message.reply_text("Sending OTP......âœ¨")
        try:
            from pyrogram import Client as PyroClient
            temp_client = PyroClient(
                f"signup_{user_id}_{int(time.time())}",
                api_id=API_ID,
                api_hash=API_HASH,
                no_updates=True
            )
            await temp_client.start()
            sent_code = await temp_client.send_code(phone)
            session_str = temp_client.export_session_string()
            await temp_client.stop()

            phone_flow[user_id] = {
                "phone": phone,
                "phone_code_hash": sent_code.phone_code_hash,
                "session_string": session_str,
            }
            await status_msg.edit_text("âœ… Check your Telegram account, OTP has been sent!")
            user_steps[user_id] = "send_otp"

        except PhoneNumberInvalid:
            await status_msg.edit_text("âŒ Invalid phone number. Please try again.")
        except PhoneNumberBanned:
            await status_msg.edit_text("âŒ This phone number is banned by Telegram.")
        except Exception as e:
            await status_msg.edit_text(f"âŒ Error: {str(e)}")
            user_steps.pop(user_id, None)

    # ---------- OTP INPUT ----------
    elif step == "send_otp":
        otp = message.text.strip()
        if not otp.isdigit():
            await message.reply_text("âŒ Please send a valid numeric OTP.")
            return
        flow_data = phone_flow.get(user_id)
        if not flow_data:
            await message.reply_text("âŒ Session expired. Please start again.")
            user_steps.pop(user_id, None)
            return
        flow_data["otp"] = otp
        await message.reply_text("ðŸ”‘ Send me your account password:")
        user_steps[user_id] = "send_password"

    # ---------- PASSWORD INPUT ----------
    elif step == "send_password":
        password = message.text.strip()
        flow_data = phone_flow.get(user_id)
        if not flow_data:
            await message.reply_text("âŒ Session expired. Please start again.")
            user_steps.pop(user_id, None)
            return

        status_msg = await message.reply_text("ðŸ”„ Adding account...")
        try:
            from pyrogram import Client as PyroClient
            temp_client = PyroClient(
                f"signin_{user_id}_{int(time.time())}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=flow_data["session_string"],
                no_updates=True
            )
            await temp_client.start()

            try:
                await temp_client.sign_in(
                    flow_data["phone"],
                    flow_data["phone_code_hash"],
                    flow_data["otp"]
                )
            except Exception as signInErr:
                err_str = str(signInErr).lower()
                if "password" in err_str or "2fa" in err_str:
                    await temp_client.check_password(password)
                else:
                    raise signInErr

            me = await temp_client.get_me()
            session_string = temp_client.export_session_string()
            await temp_client.stop()

            # Save to DB
            account_id = db.add_account(
                owner_id=user_id,
                phone=flow_data["phone"],
                session_string=session_string,
                first_name=me.first_name,
                username=me.username,
                user_id=me.id,
                account_type="phone"
            )

            user = db.get_user(user_id)
            user_name = user.get("first_name", "User") if user else "User"
            acc_mention = mention_user(me.id, me.first_name or "Unknown")
            user_mention = mention_user(user_id, user_name)

            await status_msg.edit_text(
                f"âœ… **{acc_mention}** added for report!",
                parse_mode="html"
            )

            # Log with quote style
            await send_log(client,
                f"ðŸ‘¤ User: {user_mention}\n"
                f"âž• Added Account: {acc_mention}\n"
                f"ðŸ“± Phone: `{flow_data['phone']}`",
                quote=True
            )

            # Delete the password message for security
            try:
                await message.delete()
            except Exception:
                pass

        except PhoneCodeInvalid:
            await status_msg.edit_text("âŒ Invalid OTP. Please try again from Add Account.")
        except PasswordHashInvalid:
            await status_msg.edit_text("âŒ Invalid 2FA password. Please try again.")
        except Exception as e:
            await status_msg.edit_text(f"âŒ Error adding account: {str(e)}")

        user_steps.pop(user_id, None)
        phone_flow.pop(user_id, None)

    # ---------- STRING SESSION INPUT ----------
    elif step == "send_string_session":
        session_string = message.text.strip()
        status_msg = await message.reply_text("ðŸ”„ Checking session...")

        valid, user_info = await check_session_valid(session_string)

        if valid and user_info:
            db.add_account(
                owner_id=user_id,
                session_string=session_string,
                first_name=user_info.get("first_name"),
                username=user_info.get("username"),
                user_id=user_info.get("user_id"),
                account_type="string"
            )

            user = db.get_user(user_id)
            user_name = user.get("first_name", "User") if user else "User"
            acc_mention = mention_user(user_info["user_id"], user_info.get("first_name", "Unknown"))
            user_mention = mention_user(user_id, user_name)

            await status_msg.edit_text(
                f"âœ… **{acc_mention}** Account Added!",
                parse_mode="html"
            )

            await send_log(client,
                f"ðŸ‘¤ User: {user_mention}\n"
                f"âž• Added Account: {acc_mention}\n"
                f"ðŸ”— Method: String Session",
                quote=True
            )

            # Delete the session string message for security
            try:
                await message.delete()
            except Exception:
                pass
        else:
            await status_msg.edit_text(
                "âŒ Invalid string session. Please send a valid Telethon/Pyrogram string session."
            )

        user_steps.pop(user_id, None)

    # ---------- TARGET USERNAME INPUT ----------
    elif step == "send_target_username":
        target_input = message.text.strip()
        status_msg = await message.reply_text("ðŸ” Finding target account...")

        target = None
        try:
            target = await resolve_target(client, target_input)
        except Exception:
            pass

        if not target:
            await status_msg.edit_text("âŒ Could not find the target. Please send a valid username.")
            return

        await status_msg.delete()
        report_flow[user_id] = {"target": target, "target_type": "user"}

        username_text = f"@{target['username']}" if target.get("username") else "None"
        mention_text = mention_user(target["user_id"], target.get("first_name", "Unknown"))

        text = (
            f"ðŸŽ¯ **Target Found!**\n\n"
            f"ðŸ‘¤ Name: {mention_text}\n"
            f"ðŸ†” User ID: `{target['user_id']}`\n"
            f"ðŸ“± Username: {username_text}\n\n"
            f"Select report reason:"
        )
        await message.reply_text(text, parse_mode="html", reply_markup=build_report_buttons())
        user_steps.pop(user_id, None)

    # ---------- REPORT MESSAGE INPUT ----------
    elif step == "send_report_message":
        report_msg = message.text.strip()
        if user_id not in report_flow:
            await message.reply_text("âŒ Session expired. Please start again.")
            user_steps.pop(user_id, None)
            return
        report_flow[user_id]["message"] = report_msg
        await message.reply_text("ðŸ”¢ Send me report count (how many times to report):")
        user_steps[user_id] = "send_report_count"

    # ---------- REPORT COUNT INPUT ----------
    elif step == "send_report_count":
        try:
            count = int(message.text.strip())
            if count < 1 or count > 100:
                raise ValueError
        except ValueError:
            await message.reply_text("âŒ Please send a valid number (1-100).")
            return

        if user_id not in report_flow:
            await message.reply_text("âŒ Session expired. Please start again.")
            user_steps.pop(user_id, None)
            return

        report_flow[user_id]["count"] = count
        await execute_report_attack(client, message, user_id)
        user_steps.pop(user_id, None)

    # ---------- PRIVATE GROUP LINK ----------
    elif step == "send_private_group_link":
        link = message.text.strip()
        await process_group_target(client, message, user_id, link, "private")
        user_steps.pop(user_id, None)

    # ---------- PUBLIC GROUP USERNAME ----------
    elif step == "send_public_group_link":
        target_input = message.text.strip()
        status_msg = await message.reply_text("ðŸ” Finding target group...")
        try:
            chat = await client.get_chat(target_input)
            report_flow[user_id] = {
                "target": {
                    "chat_id": chat.id,
                    "chat_title": chat.title,
                    "chat_username": chat.username
                },
                "target_type": "group_public"
            }
            await status_msg.delete()
            text = (
                f"ðŸ‘¥ **Target Group Found!**\n\n"
                f"ðŸ“› Name: {chat.title}\n"
                f"ðŸ†” ID: `{chat.id}`\n"
                f"ðŸ“± Username: @{chat.username if chat.username else 'None'}\n\n"
                f"Select report reason:"
            )
            await message.reply_text(text, parse_mode="markdown", reply_markup=build_report_buttons())
        except Exception as e:
            await status_msg.edit_text(f"âŒ Could not find the group: {str(e)}")
        user_steps.pop(user_id, None)

    # ---------- PRIVATE CHANNEL LINK ----------
    elif step == "send_private_channel_link":
        link = message.text.strip()
        await process_channel_target(client, message, user_id, link, "private")
        user_steps.pop(user_id, None)

    # ---------- PUBLIC CHANNEL USERNAME ----------
    elif step == "send_public_channel_link":
        target_input = message.text.strip()
        status_msg = await message.reply_text("ðŸ” Finding target channel...")
        try:
            chat = await client.get_chat(target_input)
            report_flow[user_id] = {
                "target": {
                    "chat_id": chat.id,
                    "chat_title": chat.title,
                    "chat_username": chat.username
                },
                "target_type": "channel_public"
            }
            await status_msg.delete()
            text = (
                f"ðŸ“¢ **Target Channel Found!**\n\n"
                f"ðŸ“› Name: {chat.title}\n"
                f"ðŸ†” ID: `{chat.id}`\n"
                f"ðŸ“± Username: @{chat.username if chat.username else 'None'}\n\n"
                f"Select report reason:"
            )
            await message.reply_text(text, parse_mode="markdown", reply_markup=build_report_buttons())
        except Exception as e:
            await status_msg.edit_text(f"âŒ Could not find the channel: {str(e)}")
        user_steps.pop(user_id, None)

    # ---------- BOT USERNAME ----------
    elif step == "send_bot_username":
        target_input = message.text.strip()
        status_msg = await message.reply_text("ðŸ” Finding target bot...")
        try:
            chat = await client.get_chat(target_input)
            report_flow[user_id] = {
                "target": {
                    "chat_id": chat.id,
                    "chat_title": chat.first_name or chat.title,
                    "chat_username": chat.username
                },
                "target_type": "bot"
            }
            await status_msg.delete()
            text = (
                f"ðŸ¤– **Target Bot Found!**\n\n"
                f"ðŸ“› Name: {chat.first_name or chat.title}\n"
                f"ðŸ†” ID: `{chat.id}`\n"
                f"ðŸ“± Username: @{chat.username if chat.username else 'None'}\n\n"
                f"Select report reason:"
            )
            await message.reply_text(text, parse_mode="markdown", reply_markup=build_report_buttons())
        except Exception as e:
            await status_msg.edit_text(f"âŒ Could not find the bot: {str(e)}")
        user_steps.pop(user_id, None)

    # ---------- GROUP LINK FOR JOIN (then report) ----------
    elif step == "send_group_link_for_join":
        link = message.text.strip()
        await join_and_report_group(client, message, user_id, link)
        user_steps.pop(user_id, None)

    # ---------- CHANNEL LINK FOR JOIN (then report) ----------
    elif step == "send_channel_link_for_join":
        link = message.text.strip()
        await join_and_report_channel(client, message, user_id, link)
        user_steps.pop(user_id, None)


# =====================================================================
#                      HELPER FUNCTIONS FOR TARGET PROCESSING
# =====================================================================

async def process_group_target(client, message, user_id, link, group_type):
    """Process a private group target - join with accounts first."""
    accounts = db.get_user_accounts(user_id)
    if not accounts:
        await message.reply_text("âŒ No accounts added. Please add accounts first.")
        return

    status_msg = await message.reply_text("ðŸ” Finding target group...")

    try:
        from pyrogram import Client as PyroClient
        first_acc = accounts[0]
        temp_client = PyroClient(
            f"grp_join_{user_id}_{int(time.time())}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=first_acc["session_string"],
            no_updates=True
        )
        await temp_client.start()

        try:
            await temp_client.join_chat(link)
        except Exception:
            pass

        chat = await temp_client.get_chat(link)
        report_flow[user_id] = {
            "target": {
                "chat_id": chat.id,
                "chat_title": chat.title,
                "chat_username": chat.username
            },
            "target_type": "group_private"
        }
        await temp_client.stop()
        await status_msg.delete()

        text = (
            f"ðŸ‘¥ **Target Group Found!**\n\n"
            f"ðŸ“› Name: {chat.title}\n"
            f"ðŸ†” ID: `{chat.id}`\n\n"
            f"Select report reason:"
        )
        await message.reply_text(text, parse_mode="markdown", reply_markup=build_report_buttons())

    except InviteHashExpired:
        await message.reply_text("âŒ Invite link has expired.")
    except ChannelPrivate:
        await message.reply_text("âŒ Cannot access this private group.")
    except Exception as e:
        await status_msg.edit_text(f"âŒ Error: {str(e)}")


async def process_channel_target(client, message, user_id, link, channel_type):
    """Process a private channel target."""
    accounts = db.get_user_accounts(user_id)
    if not accounts:
        await message.reply_text("âŒ No accounts added. Please add accounts first.")
        return

    status_msg = await message.reply_text("ðŸ” Finding target channel...")

    try:
        from pyrogram import Client as PyroClient
        first_acc = accounts[0]
        temp_client = PyroClient(
            f"ch_join_{user_id}_{int(time.time())}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=first_acc["session_string"],
            no_updates=True
        )
        await temp_client.start()

        try:
            await temp_client.join_chat(link)
        except Exception:
            pass

        chat = await temp_client.get_chat(link)
        report_flow[user_id] = {
            "target": {
                "chat_id": chat.id,
                "chat_title": chat.title,
                "chat_username": chat.username
            },
            "target_type": "channel_private"
        }
        await temp_client.stop()
        await status_msg.delete()

        text = (
            f"ðŸ“¢ **Target Channel Found!**\n\n"
            f"ðŸ“› Name: {chat.title}\n"
            f"ðŸ†” ID: `{chat.id}`\n\n"
            f"Select report reason:"
        )
        await message.reply_text(text, parse_mode="markdown", reply_markup=build_report_buttons())

    except InviteHashExpired:
        await message.reply_text("âŒ Invite link has expired.")
    except ChannelPrivate:
        await message.reply_text("âŒ Cannot access this private channel.")
    except Exception as e:
        await status_msg.edit_text(f"âŒ Error: {str(e)}")


async def join_and_report_group(client, message, user_id, link):
    """Join a private group with all accounts then proceed to report."""
    accounts = db.get_user_accounts(user_id)
    if not accounts:
        await message.reply_text("âŒ No accounts added. Please add accounts first.")
        return

    status_msg = await message.reply_text("ðŸ”„ Joining group with all accounts...")
    joined_count = 0

    for i, acc in enumerate(accounts):
        try:
            from pyrogram import Client as PyroClient
            temp_client = PyroClient(
                f"join_grp_{acc['_id']}_{int(time.time())}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=acc["session_string"],
                no_updates=True
            )
            await temp_client.start()
            try:
                await temp_client.join_chat(link)
                joined_count += 1
            except Exception:
                pass
            await temp_client.stop()
        except Exception:
            continue

        if (i + 1) % 5 == 0:
            await status_msg.edit_text(
                f"ðŸ”„ Joining... {i+1}/{len(accounts)} accounts processed, {joined_count} joined."
            )

    # Get chat info with one account
    try:
        chat = await client.get_chat(link)
    except Exception:
        # Try with first account
        try:
            from pyrogram import Client as PyroClient
            tc = PyroClient(f"info_{user_id}_{int(time.time())}", api_id=API_ID,
                           api_hash=API_HASH, session_string=accounts[0]["session_string"], no_updates=True)
            await tc.start()
            chat = await tc.get_chat(link)
            await tc.stop()
        except Exception:
            chat = None

    if chat:
        report_flow[user_id] = {
            "target": {
                "chat_id": chat.id,
                "chat_title": chat.title,
                "chat_username": chat.username
            },
            "target_type": "group_private"
        }
        await status_msg.edit_text(
            f"âœ… {joined_count}/{len(accounts)} accounts joined.\n\n"
            f"ðŸ‘¥ **Group:** {chat.title}\nðŸ†” `{chat.id}`\n\n"
            f"Select report reason:"
        )
        await message.reply_text("Select report reason:", reply_markup=build_report_buttons())
    else:
        await status_msg.edit_text(f"âœ… {joined_count} accounts joined. But couldn't get chat info.")


async def join_and_report_channel(client, message, user_id, link):
    """Join a private channel with all accounts then proceed to report."""
    accounts = db.get_user_accounts(user_id)
    if not accounts:
        await message.reply_text("âŒ No accounts added. Please add accounts first.")
        return

    status_msg = await message.reply_text("ðŸ”„ Joining channel with all accounts...")
    joined_count = 0

    for i, acc in enumerate(accounts):
        try:
            from pyrogram import Client as PyroClient
            temp_client = PyroClient(
                f"join_ch_{acc['_id']}_{int(time.time())}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=acc["session_string"],
                no_updates=True
            )
            await temp_client.start()
            try:
                await temp_client.join_chat(link)
                joined_count += 1
            except Exception:
                pass
            await temp_client.stop()
        except Exception:
            continue

        if (i + 1) % 5 == 0:
            await status_msg.edit_text(
                f"ðŸ”„ Joining... {i+1}/{len(accounts)} accounts processed, {joined_count} joined."
            )

    try:
        chat = await client.get_chat(link)
    except Exception:
        chat = None

    if chat:
        report_flow[user_id] = {
            "target": {
                "chat_id": chat.id,
                "chat_title": chat.title,
                "chat_username": chat.username
            },
            "target_type": "channel_private"
        }
        await status_msg.edit_text(
            f"âœ… {joined_count}/{len(accounts)} accounts joined.\n\n"
            f"ðŸ“¢ **Channel:** {chat.title}\nðŸ†” `{chat.id}`\n\n"
            f"Select report reason:"
        )
        await message.reply_text("Select report reason:", reply_markup=build_report_buttons())
    else:
        await status_msg.edit_text(f"âœ… {joined_count} accounts joined. But couldn't get chat info.")


# =====================================================================
#                      MASS REPORT EXECUTION
# =====================================================================

async def execute_report_attack(client, message, user_id):
    """Execute the mass report attack using all user accounts."""
    flow = report_flow.get(user_id)
    if not flow:
        await message.reply_text("âŒ Session expired. Please start again.")
        return

    target = flow.get("target", {})
    reason = flow.get("reason", "spam")
    report_message = flow.get("message", "Report")
    count = flow.get("count", 1)
    target_type = flow.get("target_type", "user")

    accounts = db.get_user_accounts(user_id)
    if not accounts:
        await message.reply_text("âŒ No accounts added. Please add accounts first.")
        return

    target_name = target.get("first_name") or target.get("chat_title", "Unknown")

    # Starting attack message
    status_msg = await message.reply_text(
        f"âš¡ **Starting Attack...**\n\n"
        f"ðŸŽ¯ Target: {target_name}\n"
        f"ðŸ“Š Accounts: {len(accounts)}\n"
        f"ðŸ”¢ Reports per account: {count}\n"
        f"ðŸ“ Reason: {report_message}"
    )

    total_reports = 0
    failed_reports = 0

    user = db.get_user(user_id)
    user_name = user.get("first_name", "User") if user else "User"
    user_mention = mention_user(user_id, user_name)

    for acc_idx, acc in enumerate(accounts):
        try:
            from pyrogram import Client as PyroClient

            # Create client from session
            try:
                temp_client = PyroClient(
                    f"report_{acc['_id']}_{int(time.time())}",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    session_string=acc["session_string"],
                    no_updates=True
                )
                await temp_client.start()
            except (SessionRevoked, AuthKeyUnregistered, UserDeactivated):
                db.deactivate_account(acc["_id"])
                failed_reports += count
                continue
            except Exception:
                failed_reports += count
                continue

            # Perform reports with this account
            for report_num in range(count):
                try:
                    # Get the target peer
                    if target_type == "user":
                        peer = target.get("user_id")
                    else:
                        peer = target.get("chat_id")

                    if peer:
                        await temp_client.report(
                            peer=peer,
                            reason=reason,
                            message=report_message
                        )
                        total_reports += 1

                        # Log each report
                        acc_mention = mention_user(
                            acc.get("user_id", 0),
                            acc.get("first_name", "Unknown")
                        )
                        await send_log(client,
                            f"âš”ï¸ Report Sent!\n"
                            f"ðŸ‘¤ By: {user_mention}\n"
                            f"ðŸ¤– Account: {acc_mention}\n"
                            f"ðŸŽ¯ Target: {target_name}\n"
                            f"ðŸ“ Reason: {report_message}\n"
                            f"ðŸ“Š Report #{total_reports}",
                            quote=True
                        )
                    else:
                        failed_reports += 1

                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                    continue
                except Exception:
                    failed_reports += 1
                    continue

                # Delay between reports (5 seconds)
                await asyncio.sleep(REPORT_DELAY)

            await temp_client.stop()

        except Exception:
            failed_reports += count
            continue

        # Update progress message
        progress_text = (
            f"âš¡ **Attack In Progress...**\n\n"
            f"âœ… Reports Sent: {total_reports}\n"
            f"âŒ Failed: {failed_reports}\n"
            f"ðŸ“Š Accounts Used: {acc_idx + 1}/{len(accounts)}"
        )
        try:
            await status_msg.edit_text(progress_text)
        except Exception:
            pass

    # Final result
    result_text = (
        f"ðŸŽ¯ **Attack Complete!**\n\n"
        f"ðŸ‘¤ Target: {target_name}\n"
        f"âœ… Total Reports Sent: {total_reports}\n"
        f"âŒ Failed Reports: {failed_reports}\n"
        f"ðŸ“Š Accounts Used: {len(accounts)}\n"
        f"ðŸ“ Reason: {report_message}"
    )

    try:
        await status_msg.edit_text(result_text)
    except Exception:
        await message.reply_text(result_text)

    # Final log
    await send_log(client,
        f"ðŸŽ¯ Attack Complete!\n"
        f"ðŸ‘¤ By: {user_mention}\n"
        f"ðŸŽ¯ Target: {target_name}\n"
        f"âœ… Reports: {total_reports}\n"
        f"âŒ Failed: {failed_reports}",
        quote=True
    )

    # Clean up
    report_flow.pop(user_id, None)


# =====================================================================
#                      /START COMMAND
# =====================================================================

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    db.add_user(user_id, message.from_user.first_name, message.from_user.username)

    if is_owner(user_id):
        await message.reply_text(
            "ðŸ‘‹ **Welcome Owner!**\n\n"
            "Available commands:\n"
            "/add_channel - Add channel/group for force join\n"
            "/rm_channel - Remove channel from force join\n"
            "/c_list - List all force join channels",
            parse_mode="markdown"
        )
        return

    # Already verified?
    if db.is_verified(user_id):
        await show_verified_menu(client, message)
        return

    # No force join channels? Auto-verify
    channels = db.get_all_channels()
    if not channels:
        db.verify_user(user_id)
        await show_verified_menu(client, message)
        return

    # Show force join requirement
    try:
        await client.send_photo(
            user_id,
            photo="https://telegra.ph/file/5e7e7f2e0c8e5c1e7e7e7.jpg",
            caption="ðŸ” **Please join the following channels to use this bot:**\n\n"
                    "Join all channels below and then click Verify.",
            parse_mode="markdown",
            reply_markup=build_force_join_buttons()
        )
    except Exception:
        await message.reply_text(
            "ðŸ” **Please join the following channels to use this bot:**\n\n"
            "Join all channels below and then click Verify.",
            parse_mode="markdown",
            reply_markup=build_force_join_buttons()
        )


async def show_verified_menu(client, message_or_query, edit=False):
    """Show the verified user menu with panel and close buttons."""
    user_id = message_or_query.from_user.id
    user = db.get_user(user_id)

    total_accounts = db.get_account_count(user_id)
    user_name = user.get("first_name", "User") if user else "User"
    user_mention = mention_user(user_id, user_name)

    caption = (
        f"ðŸ‘¤ User: {user_mention}\n"
        f"ðŸ†” User ID: <code>{user_id}</code>\n"
        f"ðŸ“Š Total Accounts Added: {total_accounts}\n"
        f"âœ… Active Accounts: {total_accounts}"
    )

    buttons = build_panel_buttons()

    if edit and hasattr(message_or_query, 'message'):
        try:
            await message_or_query.message.edit_caption(
                caption=caption,
                parse_mode="html",
                reply_markup=buttons
            )
        except Exception:
            await message_or_query.message.reply_text(
                caption, parse_mode="html", reply_markup=buttons
            )
    else:
        try:
            await client.send_photo(
                user_id,
                photo="https://telegra.ph/file/5e7e7f2e0c8e5c1e7e7e7.jpg",
                caption=caption,
                parse_mode="html",
                reply_markup=buttons
            )
        except Exception:
            await message_or_query.reply_text(
                caption, parse_mode="html", reply_markup=buttons
            )


# =====================================================================
#                      CALLBACK QUERY HANDLER
# =====================================================================

@app.on_callback_query()
async def handle_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    # ========== VERIFY ==========
    if data == "verify":
        channels = db.get_all_channels()
        all_joined = True

        for ch in channels:
            try:
                member = await client.get_chat_member(ch["chat_id"], user_id)
                if member.status in ["left", "kicked"]:
                    all_joined = False
                    break
            except UserNotParticipant:
                all_joined = False
                break
            except Exception:
                all_joined = False
                break

        if all_joined:
            db.verify_user(user_id)
            await callback.answer("âœ… Verified successfully!", show_alert=True)
            await show_verified_menu(client, callback, edit=True)
        else:
            await callback.answer(
                "âŒ You haven't joined all channels! Please join all channels first.",
                show_alert=True
            )

    # ========== PANEL ==========
    elif data == "panel":
        try:
            await callback.message.delete()
        except Exception:
            pass

        buttons = build_account_menu_buttons()
        await client.send_message(
            user_id,
            "ðŸ—³ **Pannel**\n\nSelect an option:",
            parse_mode="markdown",
            reply_markup=buttons
        )

    # ========== CLOSE ==========
    elif data == "close":
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.answer("Closed!")

    # ========== ADD ACCOUNT ==========
    elif data == "add_account":
        buttons = build_add_account_buttons()
        try:
            await callback.message.edit_text(
                "âš™ï¸ **Account Setting**\n\nSelect account type:",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            await callback.message.reply_text(
                "âš™ï¸ **Account Setting**\n\nSelect account type:",
                parse_mode="markdown",
                reply_markup=buttons
            )

    # ========== MOBILE NUMBER ==========
    elif data == "acc_phone":
        await callback.message.edit_text(
            "ðŸ“± **Send me phone number in `+918472927177` this format:**",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_phone_number"

    # ========== STRING SESSION ==========
    elif data == "acc_string":
        await callback.message.edit_text(
            "ðŸ”— **Please send me your Telegram account Telethon string session:**",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_string_session"

    # ========== MY ACCOUNT ==========
    elif data == "my_account":
        accounts = db.get_user_accounts(user_id)
        if not accounts:
            await callback.answer("âŒ No accounts added yet!", show_alert=True)
            return

        buttons = build_my_accounts_buttons(user_id)
        try:
            await callback.message.edit_text(
                "ðŸ“‹ **Your Accounts:**\n\nSelect an account to manage:",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            await callback.message.reply_text(
                "ðŸ“‹ **Your Accounts:**\n\nSelect an account to manage:",
                parse_mode="markdown",
                reply_markup=buttons
            )

    # ========== SPECIFIC ACCOUNT DETAIL ==========
    elif data.startswith("acc_") and data not in ["acc_phone", "acc_string", "add_account"]:
        account_id_str = data.replace("acc_", "")
        try:
            account_id = ObjectId(account_id_str)
        except Exception:
            await callback.answer("âŒ Invalid account!", show_alert=True)
            return

        account = db.get_account(account_id)
        if not account or account.get("owner_id") != user_id:
            await callback.answer("âŒ Account not found!", show_alert=True)
            return

        name = account.get("first_name", "Unknown")
        acc_mention = mention_user(account.get("user_id", 0), name)
        phone = account.get("phone", "N/A")
        acc_type = account.get("account_type", "phone")

        text = (
            f"ðŸ‘¤ **Account Details:**\n\n"
            f"ðŸ“› Name: {acc_mention}\n"
            f"ðŸ“± Phone: `{phone}`\n"
            f"ðŸ”— Type: {acc_type.title()}\n"
            f"âœ… Status: {'Active' if account.get('active') else 'Inactive'}"
        )

        buttons = build_account_detail_buttons(account_id)
        try:
            await callback.message.edit_text(text, parse_mode="html", reply_markup=buttons)
        except Exception:
            await callback.message.reply_text(text, parse_mode="html", reply_markup=buttons)

    # ========== REMOVE ACCOUNT ==========
    elif data.startswith("rm_acc_"):
        account_id_str = data.replace("rm_acc_", "")
        try:
            account_id = ObjectId(account_id_str)
        except Exception:
            await callback.answer("âŒ Invalid account!", show_alert=True)
            return

        account = db.get_account(account_id)
        if account and account.get("owner_id") == user_id:
            db.remove_account(account_id, user_id)
            await callback.answer("âœ… Account removed!", show_alert=True)

            accounts = db.get_user_accounts(user_id)
            if accounts:
                buttons = build_my_accounts_buttons(user_id)
                try:
                    await callback.message.edit_text(
                        "ðŸ“‹ **Your Accounts:**\n\nSelect an account to manage:",
                        parse_mode="markdown",
                        reply_markup=buttons
                    )
                except Exception:
                    pass
            else:
                try:
                    await callback.message.edit_text(
                        "âŒ No accounts left.",
                        parse_mode="markdown",
                        reply_markup=build_account_menu_buttons()
                    )
                except Exception:
                    pass
        else:
            await callback.answer("âŒ Account not found!", show_alert=True)

    # ========== START ATTACK ==========
    elif data == "start_attack":
        accounts = db.get_user_accounts(user_id)
        if not accounts:
            await callback.answer("âŒ No accounts added! Please add accounts first.", show_alert=True)
            return

        buttons = build_target_type_buttons()
        try:
            await callback.message.edit_text(
                "âš¡ **Select Target Type:**",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            await callback.message.reply_text(
                "âš¡ **Select Target Type:**",
                parse_mode="markdown",
                reply_markup=buttons
            )

    # ========== TARGET: USER ==========
    elif data == "target_user":
        await callback.message.edit_text(
            "ðŸ‘¤ **Send me target username** (e.g., @target_user)\n\n"
            "Or share the user's profile using the inline keyboard button below.",
            parse_mode="markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ðŸ‘¤ Select User", switch_inline_query_current_chat="")]
            ])
        )
        user_steps[user_id] = "send_target_username"

    # ========== TARGET: GROUP ==========
    elif data == "target_group":
        buttons = build_group_type_buttons()
        try:
            await callback.message.edit_text(
                "ðŸ‘¥ **Select Group Type:**",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            pass

    # ========== TARGET: CHANNEL ==========
    elif data == "target_channel":
        buttons = build_channel_type_buttons()
        try:
            await callback.message.edit_text(
                "ðŸ“¢ **Select Channel Type:**",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            pass

    # ========== TARGET: BOT ==========
    elif data == "target_bot":
        await callback.message.edit_text(
            "ðŸ¤– **Send me the bot's username:** (e.g., @example_bot)",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_bot_username"

    # ========== GROUP: PRIVATE ==========
    elif data == "grp_private":
        await callback.message.edit_text(
            "ðŸ”’ **Send me valid invite link of the group:**",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_private_group_link"

    # ========== GROUP: PUBLIC ==========
    elif data == "grp_public":
        await callback.message.edit_text(
            "ðŸŒ **Send me the group username or link:** (e.g., @groupname or https://t.me/groupname)",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_public_group_link"

    # ========== CHANNEL: PRIVATE ==========
    elif data == "ch_private":
        await callback.message.edit_text(
            "ðŸ”’ **Send me valid invite link of the channel:**",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_private_channel_link"

    # ========== CHANNEL: PUBLIC ==========
    elif data == "ch_public":
        await callback.message.edit_text(
            "ðŸŒ **Send me the channel username or link:** (e.g., @channelname or https://t.me/channelname)",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_public_channel_link"

    # ========== MODE SELECTION (Owner) ==========
    elif data == "mode_normal":
        if not is_owner(user_id):
            return
        temp = temp_data.get(user_id)
        if not temp:
            await callback.answer("âŒ Session expired!", show_alert=True)
            return

        chat_id = temp["chat_id"]
        chat_title = temp["chat_title"]
        chat_username = temp.get("chat_username")

        try:
            link = await client.create_chat_invite_link(chat_id)
            invite_link = link.invite
        except Exception as e:
            await callback.answer(f"âŒ Error creating link: {str(e)}", show_alert=True)
            return

        db.add_channel(chat_id, chat_title, chat_username, invite_link, mode="normal")

        await callback.message.edit_text(
            f"âœ… **Channel Added Successfully!**\n\n"
            f"ðŸ“¢ Name: {chat_title}\n"
            f"ðŸ†” ID: `{chat_id}`\n"
            f"ðŸŒ Mode: Normal\n"
            f"ðŸ”— Link: {invite_link}",
            parse_mode="markdown"
        )
        temp_data.pop(user_id, None)

    elif data == "mode_request":
        if not is_owner(user_id):
            return
        temp = temp_data.get(user_id)
        if not temp:
            await callback.answer("âŒ Session expired!", show_alert=True)
            return

        chat_id = temp["chat_id"]
        chat_title = temp["chat_title"]
        chat_username = temp.get("chat_username")

        try:
            link = await client.create_chat_invite_link(chat_id, creates_join_request=True)
            invite_link = link.invite
        except Exception as e:
            await callback.answer(f"âŒ Error creating link: {str(e)}", show_alert=True)
            return

        db.add_channel(chat_id, chat_title, chat_username, invite_link, mode="request")

        await callback.message.edit_text(
            f"âœ… **Channel Added Successfully!**\n\n"
            f"ðŸ“¢ Name: {chat_title}\n"
            f"ðŸ†” ID: `{chat_id}`\n"
            f"ðŸ”— Mode: Request\n"
            f"ðŸ”— Link: {invite_link}",
            parse_mode="markdown"
        )
        temp_data.pop(user_id, None)

    # ========== BACK BUTTONS ==========
    elif data == "back_main":
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_verified_menu(client, callback, edit=False)

    elif data == "back_panel":
        buttons = build_account_menu_buttons()
        try:
            await callback.message.edit_text(
                "ðŸ—³ **Pannel**\n\nSelect an option:",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            pass

    elif data == "back_target":
        buttons = build_target_type_buttons()
        try:
            await callback.message.edit_text(
                "âš¡ **Select Target Type:**",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            pass

    # ========== REPORT CATEGORY BUTTONS ==========
    elif data.startswith("rpt_sub_"):
        category_key = data.replace("rpt_sub_", "")
        buttons = get_subcategory_buttons(category_key)
        try:
            await callback.message.edit_text(
                "ðŸ“ **Select report reason:**",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            pass

    elif data.startswith("rpt_final_"):
        category_key = data.replace("rpt_final_", "")
        reason, report_message = get_report_reason(category_key)

        if user_id in report_flow:
            report_flow[user_id]["reason"] = reason
            report_flow[user_id]["report_msg"] = report_message
        else:
            report_flow[user_id] = {
                "reason": reason,
                "report_msg": report_message,
            }

        await callback.message.edit_text(
            f"ðŸ“ **Report Reason:** {report_message}\n\n"
            f"ðŸ’¬ Send me the report message:",
            parse_mode="markdown"
        )
        user_steps[user_id] = "send_report_message"

    elif data == "rpt_back":
        buttons = build_report_buttons()
        try:
            await callback.message.edit_text(
                "ðŸ“ **Select report reason:**",
                parse_mode="markdown",
                reply_markup=buttons
            )
        except Exception:
            pass

    # ========== UNKNOWN CALLBACK ==========
    else:
        await callback.answer()


# =====================================================================
#                      INLINE QUERY HANDLER
# =====================================================================

@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query):
    """Handle inline queries for user selection in target finding."""
    query = inline_query.query.strip()
    if not query:
        return

    try:
        users = await client.get_users(query)
        if not isinstance(users, list):
            users = [users]

        results = []
        for user in users:
            full_name = f"{user.first_name} {user.last_name or ''}".strip()
            results.append(
                InlineQueryResultArticle(
                    title=full_name,
                    input_message_content=InputTextMessageContent(
                        message_text=f"@{user.username}" if user.username else str(user.id)
                    ),
                    description=f"ID: {user.id} | @{user.username or 'No username'}"
                )
            )

        await inline_query.answer(results, cache_time=0)
    except Exception:
        await inline_query.answer([], cache_time=0)


# =====================================================================
#                      CHAT MEMBER UPDATES (JOIN LOG)
# =====================================================================

@app.on_chat_member_updated()
async def handle_member_update(client: Client, update):
    """Log when users join/request to join force join channels."""
    if not update.new_chat_member:
        return

    user = update.new_chat_member.user
    chat_id = update.chat.id

    # Check if this is a force join channel
    channel = db.get_channel(chat_id)
    if not channel:
        return

    # Skip owner
    if user.id == OWNER_ID:
        return

    # Save/update user
    db.add_user(user.id, user.first_name, user.username)

    user_name = user.first_name or "Unknown"
    user_mention = mention_user(user.id, user_name)

    mode = channel.get("mode", "normal")
    mode_text = "ðŸ”— Request" if mode == "request" else "ðŸŒ Normal"
    link = channel.get("invite_link", "N/A")

    # Log with quote style
    await send_log(client,
        f"ðŸ‘¤ User: {user_mention}\n"
        f"ðŸ†” User ID: <code>{user.id}</code>\n"
        f"ðŸ”— Link: {link}\n"
        f"ðŸ“Š Mode: {mode_text}",
        quote=True
    )


# =====================================================================
#                      START BOT
# =====================================================================

async def main():
    print("âš”ï¸ Mass Reporter Bot")
    print("=" * 40)
    print(f"ðŸ‘¤ Owner ID: {OWNER_ID}")
    print(f"ðŸ“ Log Group: {LOG_GROUP}")
    print(f"â± Report Delay: {REPORT_DELAY}s")
    print("=" * 40)
    print("ðŸš€ Starting...")

    await app.start()
    me = await app.get_me()
    print(f"âœ… Bot started as @{me.username}")
    print("ðŸ”´ Press Ctrl+C to stop.")

    await idle()

    await app.stop()
    print("ðŸ”´ Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
