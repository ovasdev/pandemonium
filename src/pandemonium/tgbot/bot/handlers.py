"""Telegram bot command and message handlers."""

import logging
import re
from pathlib import Path

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import pandemonium.tgbot.db as db_mod
from pandemonium.tgbot.bot.formatters import (
    format_active_status,
    format_history,
    format_status_message,
    format_tokens,
    welcome_message,
)
from pandemonium.tgbot.config import AppConfig, ConfigError, load_config, scan_personas
from pandemonium.tgbot.session.manager import SessionManager
from pandemonium.tgbot.session.state import SessionState

logger = logging.getLogger(__name__)

router = Router(name="main")


def _is_group_chat(message: Message) -> bool:
    return message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


def _is_bot_mentioned(message: Message, bot_username: str) -> bool:
    """Check if the bot is mentioned via @username in message text or caption."""
    text = message.text or message.caption or ""
    return bool(re.search(rf"@{re.escape(bot_username)}\b", text, re.IGNORECASE))


def _strip_mention(text: str, bot_username: str) -> str:
    """Remove @bot_username from text and clean up extra whitespace."""
    cleaned = re.sub(rf"\s*@{re.escape(bot_username)}\b\s*", " ", text, flags=re.IGNORECASE)
    return cleaned.strip()


def _get_active_project(config: AppConfig, session_manager: SessionManager):
    """Get the active project config from session manager."""
    return config.get_project(session_manager.active_project_id) or config.default_project


@router.message(CommandStart())
async def cmd_start(message: Message, config: AppConfig, session_manager: SessionManager) -> None:
    """Handle /start — greet authorized user."""
    user_id = message.from_user.id  # type: ignore[union-attr]
    user_name = config.get_user_name(user_id) or "User"
    project_name = _get_active_project(config, session_manager).name
    await message.answer(welcome_message(user_name, project_name), parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help — list available commands."""
    text = (
        "<b>Commands</b>\n\n"
        "/projects — switch active project\n"
        "/personas — switch active persona\n"
        "/status — current request status\n"
        "/history — recent requests\n"
        "/tokens — token usage stats\n"
        "/clear — reset conversation context\n"
        "/reload — reload config without restart\n"
        "/protos &lt;text&gt; — send prompt (works in groups)"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("status"))
async def cmd_status(
    message: Message,
    config: AppConfig,
    db: aiosqlite.Connection,
    session_manager: SessionManager,
) -> None:
    """Handle /status — show active request status."""
    active = session_manager.active_session
    if active and active.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
        project = _get_active_project(config, session_manager)
        row = await db_mod.get_active_request(db, project.id)
        if row:
            await message.answer(
                format_active_status(row["request_number"], row["created_at"])
            )
            return
    await message.answer("No active requests.")


@router.message(Command("history"))
async def cmd_history(
    message: Message,
    config: AppConfig,
    db: aiosqlite.Connection,
    session_manager: SessionManager,
) -> None:
    """Handle /history — show recent requests."""
    project = _get_active_project(config, session_manager)
    rows = await db_mod.get_recent_requests(db, project.id, limit=10)
    await message.answer(format_history(rows), parse_mode=ParseMode.HTML)


@router.message(Command("clear"))
async def cmd_clear(
    message: Message,
    session_manager: SessionManager,
) -> None:
    """Handle /clear — reset Claude Code session (start fresh conversation)."""
    active = session_manager.active_session
    if active and active.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
        await message.answer("Cannot clear while a request is running. Cancel it first.")
        return

    had_session = session_manager.claude_session_id is not None
    session_manager.clear_session()
    if had_session:
        await message.answer("Session cleared. Next message starts a fresh conversation.")
    else:
        await message.answer("No active session. Next message starts a fresh conversation.")


@router.message(Command("reload"))
async def cmd_reload(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
    config_path: Path,
) -> None:
    """Handle /reload — reload config.yaml without restarting the bot."""
    try:
        new_config = load_config(config_path)
    except ConfigError as e:
        await message.answer(f"Config reload failed: {e}")
        return

    session_manager.update_config(new_config)
    # Update the dispatcher reference via the router's parent
    message.bot.session  # noqa: just to ensure bot is accessible
    router.parent_router.workflow_data["config"] = new_config  # type: ignore[union-attr]

    project_names = [p.name for p in new_config.projects]
    await message.answer(
        f"Config reloaded. Projects ({len(project_names)}):\n"
        + "\n".join(f"• {name}" for name in project_names)
    )


@router.message(Command("projects"))
async def cmd_projects(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
) -> None:
    """Handle /projects — show project list as inline buttons."""
    active_id = session_manager.active_project_id
    buttons: list[list[InlineKeyboardButton]] = []
    for project in config.projects:
        label = f"{'✦ ' if project.id == active_id else ''}{project.name}"
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"project:{project.id}",
            ),
        ])
    await message.answer(
        f"Projects ({len(config.projects)}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.message(Command("personas"))
async def cmd_personas(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
) -> None:
    """Handle /personas — show persona list for the default project only."""
    default_project = config.default_project
    personas = scan_personas(default_project.path)
    if not personas:
        await message.answer("No personas found.")
        return

    active_persona = session_manager.active_persona
    buttons: list[list[InlineKeyboardButton]] = []
    for name in personas:
        marker = "✦ " if name == active_persona else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{marker}{name}",
                callback_data=f"persona:{name}",
            ),
        ])

    await message.answer(
        f"Personas ({default_project.name}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.message(Command("tokens"))
async def cmd_tokens(
    message: Message,
    config: AppConfig,
    db: aiosqlite.Connection,
    session_manager: SessionManager,
) -> None:
    """Handle /tokens — show total token usage."""
    project = _get_active_project(config, session_manager)
    totals = await db_mod.get_token_totals(db, project.id)
    rows = await db_mod.get_recent_requests(db, project.id, limit=10000)
    await message.answer(format_tokens(project.name, len(rows), totals), parse_mode=ParseMode.HTML)


def _build_reply_context(message: Message) -> str:
    """Build a prompt with reply chain context (up to 2 levels)."""
    user_text = message.text or ""
    reply_to = message.reply_to_message
    if not reply_to:
        return user_text

    parts: list[str] = []

    # Level 2: reply-to's reply-to (grandparent)
    grandparent = reply_to.reply_to_message
    if grandparent:
        gp_author = grandparent.from_user.full_name if grandparent.from_user else "Unknown"
        gp_text = grandparent.text or grandparent.caption or "[no text]"
        parts.append(f"[Message from {gp_author}]:\n{gp_text}")

    # Level 1: the message being replied to (parent)
    parent_author = reply_to.from_user.full_name if reply_to.from_user else "Unknown"
    parent_text = reply_to.text or reply_to.caption or "[no text]"
    parts.append(f"[Reply to message from {parent_author}]:\n{parent_text}")

    # Level 0: user's own message
    parts.append(f"[User's message (reply)]:\n{user_text}")

    return "\n\n".join(parts)


@router.message(F.reply_to_message & F.text & ~F.text.startswith("/"))
async def handle_reply_message(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
    db: aiosqlite.Connection,
    bot_username: str,
) -> None:
    """Handle a reply — either a permission answer or a new request with context."""
    reply_to = message.reply_to_message
    if not reply_to:
        return

    # Check if this is a reply to a permission/clarification question
    interaction = await db.execute(
        "SELECT i.*, r.id as req_id FROM interactions i "
        "JOIN requests r ON i.request_id = r.id "
        "WHERE i.message_id = ? AND i.direction = 'from_claude'",
        (reply_to.message_id,),
    )
    row = await interaction.fetchone()
    if row:
        # Permission reply — existing behavior
        request_id = row["req_id"]
        text = message.text or ""
        await session_manager.handle_user_reply(request_id, text)
        return

    # Regular reply — build context chain and start a new request
    if _is_group_chat(message) and not _is_bot_mentioned(message, bot_username):
        return

    prompt = _build_reply_context(message)
    prompt = _strip_mention(prompt, bot_username)
    await _start_text_request(message, config, session_manager, prompt)


async def _download_file(bot: Bot, file_id: str, dest: Path) -> Path:
    """Download a Telegram file to the destination directory. Returns saved path."""
    dest.mkdir(parents=True, exist_ok=True)
    tg_file = await bot.get_file(file_id)
    assert tg_file.file_path is not None
    # Use original filename from Telegram storage (e.g. "documents/file_1.pdf")
    extension = Path(tg_file.file_path).suffix or ""
    local_name = f"{file_id}{extension}"
    local_path = dest / local_name
    await bot.download_file(tg_file.file_path, destination=local_path)
    return local_path


@router.message(F.document)
async def handle_document_message(
    message: Message,
    bot: Bot,
    config: AppConfig,
    session_manager: SessionManager,
    bot_username: str,
) -> None:
    """Handle a document (file) message — download and pass to Claude Code."""
    if _is_group_chat(message) and not _is_bot_mentioned(message, bot_username):
        return

    active = session_manager.active_session
    if active and active.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
        await message.reply("A request is already in progress. Please wait or cancel it.")
        return

    doc = message.document
    assert doc is not None
    original_name = doc.file_name or "file"
    uploads_dir = config.storage.uploads_path
    local_path = await _download_file(bot, doc.file_id, uploads_dir)
    # Rename to preserve original filename (add file_id prefix to avoid collisions)
    final_path = uploads_dir / f"{doc.file_unique_id}_{original_name}"
    local_path.rename(final_path)

    caption = _strip_mention(message.caption or "", bot_username)
    prompt = f"User sent a file: {final_path}\nOriginal filename: {original_name}"
    if caption:
        prompt += f"\n\nUser message: {caption}"

    await _start_file_request(message, config, session_manager, prompt)


@router.message(F.photo)
async def handle_photo_message(
    message: Message,
    bot: Bot,
    config: AppConfig,
    session_manager: SessionManager,
    bot_username: str,
) -> None:
    """Handle a photo message — download largest size and pass to Claude Code."""
    if _is_group_chat(message) and not _is_bot_mentioned(message, bot_username):
        return

    active = session_manager.active_session
    if active and active.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
        await message.reply("A request is already in progress. Please wait or cancel it.")
        return

    assert message.photo is not None
    # Last element is the largest photo size
    photo = message.photo[-1]
    uploads_dir = config.storage.uploads_path
    local_path = await _download_file(bot, photo.file_id, uploads_dir)

    caption = _strip_mention(message.caption or "", bot_username)
    prompt = f"User sent a photo: {local_path}"
    if caption:
        prompt += f"\n\nUser message: {caption}"

    await _start_file_request(message, config, session_manager, prompt)


async def _start_file_request(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
    prompt: str,
) -> None:
    """Common logic for starting a request from a file message."""
    user_id = message.from_user.id  # type: ignore[union-attr]
    project = _get_active_project(config, session_manager)

    status_text = format_status_message(0, SessionState.RUNNING)
    status_msg = await message.reply(
        status_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Cancel", callback_data="cancel:0")],
        ]),
    )

    try:
        req_number = await session_manager.create_request(
            project_id=project.id,
            user_id=user_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            status_message_id=status_msg.message_id,
            prompt=prompt,
        )

        session = session_manager.active_session
        request_id = session.request_id if session else 0
        await status_msg.edit_text(
            format_status_message(req_number, SessionState.RUNNING),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Cancel",
                    callback_data=f"cancel:{request_id}",
                )],
            ]),
        )
    except RuntimeError:
        await status_msg.edit_text("A request is already in progress.")
    except Exception:
        logger.exception("Failed to create request")
        await status_msg.edit_text("Failed to start Claude Code.")


async def _start_text_request(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
    prompt: str,
) -> None:
    """Common logic for starting a text request."""
    user_id = message.from_user.id  # type: ignore[union-attr]
    project = _get_active_project(config, session_manager)

    active = session_manager.active_session
    if active and active.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
        await message.reply("A request is already in progress. Please wait or cancel it.")
        return

    status_text = format_status_message(0, SessionState.RUNNING)
    status_msg = await message.reply(
        status_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Cancel", callback_data="cancel:0")],
        ]),
    )

    try:
        req_number = await session_manager.create_request(
            project_id=project.id,
            user_id=user_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            status_message_id=status_msg.message_id,
            prompt=prompt,
        )

        session = session_manager.active_session
        request_id = session.request_id if session else 0
        await status_msg.edit_text(
            format_status_message(req_number, SessionState.RUNNING),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Cancel",
                    callback_data=f"cancel:{request_id}",
                )],
            ]),
        )
    except RuntimeError:
        await status_msg.edit_text("A request is already in progress.")
    except Exception:
        logger.exception("Failed to create request")
        await status_msg.edit_text("Failed to start Claude Code.")


@router.message(Command("protos"))
async def cmd_protos(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
) -> None:
    """Handle /protos <text> — start a Claude Code request (works in groups)."""
    prompt = (message.text or "").split(maxsplit=1)[1] if (message.text or "").strip().count(" ") >= 1 else ""
    if not prompt.strip():
        await message.reply("Usage: /protos <your message>")
        return
    await _start_text_request(message, config, session_manager, prompt)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(
    message: Message,
    config: AppConfig,
    session_manager: SessionManager,
    bot_username: str,
) -> None:
    """Handle a plain text message — start a Claude Code request."""
    # In group chats, only respond when the bot is @mentioned
    if _is_group_chat(message) and not _is_bot_mentioned(message, bot_username):
        return

    prompt = _strip_mention(message.text or "", bot_username)
    await _start_text_request(message, config, session_manager, prompt)
