"""Telegram bot command and message handlers."""

import asyncio
import logging
import os
import re
import signal
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
        "/reboot — restart the bot\n"
        "/find — search files in filestorage2\n"
        "/qrand [NdX] — quantum random dice\n"
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


@router.message(Command("reboot"))
async def cmd_reboot(
    message: Message,
    session_manager: SessionManager,
) -> None:
    """Handle /reboot — restart the bot via restart.sh."""
    active = session_manager.active_session
    if active and active.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
        await message.answer("Cannot reboot while a request is running. Cancel it first.")
        return

    bot_root = Path(__file__).resolve().parents[4]
    start_script = bot_root / "start.sh"
    if not start_script.exists():
        await message.answer("start.sh not found.")
        return

    await message.answer("Rebooting...")
    pid = os.getpid()
    # Spawn a fully detached shell that waits for this process to die,
    # then starts the bot fresh. Using shell + disown to survive parent exit.
    await asyncio.create_subprocess_shell(
        f"(while kill -0 {pid} 2>/dev/null; do sleep 0.5; done; "
        f"cd {bot_root} && bash start.sh) &",
        start_new_session=True,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        stdin=asyncio.subprocess.DEVNULL,
    )
    # Now trigger graceful shutdown
    os.kill(pid, signal.SIGTERM)


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
    """Handle /personas — show persona list for the currently active project."""
    project = _get_active_project(config, session_manager)
    personas = scan_personas(project.path)
    if not personas:
        await message.answer(f"No personas found for {project.name}.")
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
        f"Personas ({project.name}):",
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

    # When resuming a Claude session, the conversation history is already
    # in the session context — skip reply chain to avoid duplication.
    if session_manager.claude_session_id:
        prompt = message.text or ""
    else:
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


_QRAND_SCRIPT = Path(__file__).resolve().parents[3] / "pandemonium" / "tgbot" / ".." / ".." / ".." / ".pandemonium" / "tools" / "quantum_random.sh"
# Resolve once at import time
_QRAND_SCRIPT = (Path(__file__).resolve().parents[4] / ".pandemonium" / "tools" / "quantum_random.sh")

_DICE_PRESETS = [
    ("d4", 1, 4),
    ("d6", 1, 6),
    ("d8", 1, 8),
    ("d10", 1, 10),
    ("d12", 1, 12),
    ("d20", 1, 20),
    ("d100", 1, 100),
]


async def _run_quantum_random(count: int, from_val: int, to_val: int) -> str:
    """Run quantum_random.sh and return its stdout or an error message."""
    proc = await asyncio.create_subprocess_exec(
        str(_QRAND_SCRIPT), str(count), str(from_val), str(to_val),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        return "Квантовая кость недоступна."
    return stdout.decode().strip()


def _parse_dice_notation(text: str) -> tuple[int, int] | None:
    """Parse NdX notation (e.g. '5d6'). Returns (count, sides) or None."""
    m = re.fullmatch(r"(\d+)[dDдД](\d+)", text.strip())
    if m:
        count, sides = int(m.group(1)), int(m.group(2))
        if count >= 1 and sides >= 2:
            return count, sides
    return None


@router.message(Command("qrand"))
async def cmd_qrand(message: Message) -> None:
    """Handle /qrand [NdX] — quantum random dice."""
    args = (message.text or "").split(maxsplit=1)[1].strip() if (message.text or "").strip().count(" ") >= 1 else ""

    if not args:
        # No arguments — show dice preset panel
        buttons: list[list[InlineKeyboardButton]] = []
        row: list[InlineKeyboardButton] = []
        for name, from_val, to_val in _DICE_PRESETS:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"qrand:1:{from_val}:{to_val}",
            ))
            if len(row) == 4:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        await message.answer(
            "🎲 Квантовая кость",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
        return

    # Try to parse NdX notation
    parsed = _parse_dice_notation(args)
    if not parsed:
        await message.reply("Формат: /qrand NdX (например, /qrand 5d6)")
        return

    count, sides = parsed
    if count > 100:
        await message.reply("Максимум 100 бросков за раз.")
        return

    result = await _run_quantum_random(count, 1, sides)
    numbers = result.split("\n")
    total = sum(int(n) for n in numbers if n.isdigit())
    header = f"🎲 {count}d{sides}"
    if count == 1:
        await message.reply(f"{header} → <b>{result}</b>", parse_mode=ParseMode.HTML)
    else:
        await message.reply(
            f"{header} → {', '.join(numbers)}\nСумма: <b>{total}</b>",
            parse_mode=ParseMode.HTML,
        )


# ---------------------------------------------------------------------------
# /find — search files in filestorage2
# ---------------------------------------------------------------------------

_FS2_BASE = "http://192.168.1.105:4733"


def _parse_find_query(raw: str) -> dict:
    """Parse /find query into structured filters.

    Format (all parts optional, at least one required):
        #tag1 #tag2
        collections: col1, col2
        not: #nottag1 #nottag2
        collections: notcol1, notcol2
        title: part of the title
        artefact: name
        count: 5
    """
    result: dict = {
        "tags": [],
        "collections": [],
        "not_tags": [],
        "not_collections": [],
        "title": None,
        "artefact": None,
        "count": 5,
    }

    lines = raw.strip().splitlines()
    in_not = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # count: N
        m = re.match(r"^count:\s*(\d+)", stripped, re.IGNORECASE)
        if m:
            result["count"] = max(1, min(int(m.group(1)), 50))
            continue

        # title: ...
        m = re.match(r"^title:\s*(.+)", stripped, re.IGNORECASE)
        if m:
            result["title"] = m.group(1).strip()
            continue

        # artefact: ... (also artifact)
        m = re.match(r"^arte?fact:\s*(.+)", stripped, re.IGNORECASE)
        if m:
            result["artefact"] = m.group(1).strip()
            continue

        # not: ... (may contain tags inline)
        m = re.match(r"^not:\s*(.*)", stripped, re.IGNORECASE)
        if m:
            in_not = True
            rest = m.group(1).strip()
            if rest:
                not_tags = re.findall(r"#([\w/\-]+)", rest)
                result["not_tags"].extend(not_tags)
            continue

        # collections: ...
        m = re.match(r"^collections?:\s*(.+)", stripped, re.IGNORECASE)
        if m:
            cols = [c.strip() for c in m.group(1).split(",") if c.strip()]
            if in_not:
                result["not_collections"].extend(cols)
            else:
                result["collections"].extend(cols)
            continue

        # Standalone tags (#tag1 #tag2 ...)
        tags_found = re.findall(r"#([\w/\-]+)", stripped)
        if tags_found:
            if in_not:
                result["not_tags"].extend(tags_found)
            else:
                result["tags"].extend(tags_found)
            continue

    return result


def _format_file_card(file_data: dict) -> str:
    """Format a file as an HTML card for Telegram."""
    fid = file_data.get("id", "?")
    name = file_data.get("original_filename", "?")
    desc = file_data.get("description") or ""
    mime = file_data.get("mime_type", "")
    size = file_data.get("size", 0)
    created = file_data.get("created_at", "")[:10]

    tags = file_data.get("tags") or []
    tag_names = [f"#{t['name']}" for t in tags]
    collections = file_data.get("collections") or []
    col_names = [c["name"] for c in collections]

    # Icon by mime
    if mime.startswith("image/"):
        icon = "🖼"
    elif mime.startswith("audio/"):
        icon = "🎵"
    elif mime.startswith("video/"):
        icon = "🎬"
    elif "pdf" in mime:
        icon = "📕"
    else:
        icon = "📄"

    # Size formatting
    if size >= 1_048_576:
        size_str = f"{size / 1_048_576:.1f} MB"
    elif size >= 1024:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size} B"

    lines = [f"{icon} <b>{name}</b>"]
    if desc:
        lines.append(desc[:200])
    if tag_names:
        lines.append(f"Теги: {' '.join(tag_names)}")
    if col_names:
        lines.append(f"Коллекции: {', '.join(col_names)}")
    lines.append(f"{size_str} · {created} · <code>id:{fid}</code>")

    return "\n".join(lines)


@router.message(Command("find"))
async def cmd_find(message: Message) -> None:
    """Handle /find — search files in filestorage2 on Raspberry Pi."""
    import aiohttp

    raw = (message.text or "").split(maxsplit=1)[1] if (message.text or "").strip().count(" ") >= 1 else ""
    if not raw.strip():
        await message.reply(
            "<b>Usage:</b>\n"
            "<code>/find #tag1 #tag2\n"
            "collections: col1, col2\n"
            "not: #excl_tag\n"
            "collections: excl_col\n"
            "title: search text\n"
            "count: 5</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    query = _parse_find_query(raw)

    # Check that at least one filter is set
    has_filter = (
        query["tags"]
        or query["collections"]
        or query["title"]
        or query["artefact"]
    )
    if not has_filter:
        await message.reply("Нужен хотя бы один фильтр: теги, коллекции, title или artefact.")
        return

    api_key = os.environ.get("RASPBERY_FILESTORAGE_KEY", "")
    if not api_key:
        await message.reply("RASPBERY_FILESTORAGE_KEY не настроен.")
        return

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as http:
            # Resolve tag names → IDs
            tag_id_map: dict[str, int] = {}
            if query["tags"] or query["not_tags"]:
                async with http.get(f"{_FS2_BASE}/api/tags", headers=headers) as resp:
                    if resp.status == 200:
                        all_tags = await resp.json()
                        tag_id_map = {t["name"]: t["id"] for t in all_tags}

            # Resolve collection names → IDs
            col_id_map: dict[str, int] = {}
            if query["collections"] or query["not_collections"]:
                async with http.get(f"{_FS2_BASE}/api/collections", headers=headers) as resp:
                    if resp.status == 200:
                        all_cols = await resp.json()
                        col_id_map = {c["name"]: c["id"] for c in all_cols}

            # Build query params for /api/files
            params: dict[str, str] = {"sort": "created_at:desc"}

            # Include tags (intersection)
            include_tag_ids = []
            for t in query["tags"]:
                tid = tag_id_map.get(t)
                if tid is None:
                    await message.reply(f"Тег <code>#{t}</code> не найден.", parse_mode=ParseMode.HTML)
                    return
                include_tag_ids.append(tid)
            if include_tag_ids:
                params["tag_ids"] = ",".join(str(i) for i in include_tag_ids)

            # Include collections (union)
            include_col_ids = []
            for c in query["collections"]:
                cid = col_id_map.get(c)
                if cid is None:
                    await message.reply(f"Коллекция <code>{c}</code> не найдена.", parse_mode=ParseMode.HTML)
                    return
                include_col_ids.append(cid)
            if include_col_ids:
                params["collection_ids"] = ",".join(str(i) for i in include_col_ids)

            # Exclude tags/collections — resolve IDs for client-side filtering
            exclude_tag_ids = set()
            for t in query["not_tags"]:
                tid = tag_id_map.get(t)
                if tid is not None:
                    exclude_tag_ids.add(tid)

            exclude_col_ids = set()
            for c in query["not_collections"]:
                cid = col_id_map.get(c)
                if cid is not None:
                    exclude_col_ids.add(cid)

            # If title or artefact search — use /api/files/search
            if query["title"] or query["artefact"]:
                search_q = query["title"] or query["artefact"] or ""
                search_params = {"q": search_q, "limit": "50", "offset": "0"}
                async with http.get(
                    f"{_FS2_BASE}/api/files/search", headers=headers, params=search_params,
                ) as resp:
                    if resp.status != 200:
                        await message.reply(f"Ошибка поиска: {resp.status}")
                        return
                    search_results = await resp.json()

                # search_results may be a list or {"files": [...]}
                if isinstance(search_results, dict):
                    files = search_results.get("files") or search_results.get("data") or []
                else:
                    files = search_results

                # Apply tag/collection filters client-side on search results
                if include_tag_ids:
                    files = [
                        f for f in files
                        if all(
                            tid in {t["id"] for t in (f.get("tags") or [])}
                            for tid in include_tag_ids
                        )
                    ]
                if include_col_ids:
                    files = [
                        f for f in files
                        if any(
                            cid in {c["id"] for c in (f.get("collections") or [])}
                            for cid in include_col_ids
                        )
                    ]
            else:
                # Pure tag/collection filter via API
                async with http.get(
                    f"{_FS2_BASE}/api/files", headers=headers, params=params,
                ) as resp:
                    if resp.status != 200:
                        await message.reply(f"Ошибка запроса: {resp.status}")
                        return
                    api_result = await resp.json()

                if isinstance(api_result, dict):
                    files = api_result.get("files") or api_result.get("data") or []
                else:
                    files = api_result

            # Client-side exclusion filters
            if exclude_tag_ids:
                files = [
                    f for f in files
                    if not exclude_tag_ids.intersection(
                        {t["id"] for t in (f.get("tags") or [])}
                    )
                ]
            if exclude_col_ids:
                files = [
                    f for f in files
                    if not exclude_col_ids.intersection(
                        {c["id"] for c in (f.get("collections") or [])}
                    )
                ]

            # Apply title filter as substring match if combined with tags
            if query["title"] and (include_tag_ids or include_col_ids):
                needle = query["title"].lower()
                files = [
                    f for f in files
                    if needle in (f.get("original_filename") or "").lower()
                    or needle in (f.get("description") or "").lower()
                ]

            total_found = len(files)
            count = query["count"]
            display_files = files[:count]

            if not display_files:
                await message.reply("Ничего не найдено.")
                return

            # Send each file as a separate card
            for f in display_files:
                card = _format_file_card(f)
                await message.answer(card, parse_mode=ParseMode.HTML)

            if total_found > count:
                await message.answer(
                    f"Найдено файлов: <b>{total_found}</b> (показано {count})",
                    parse_mode=ParseMode.HTML,
                )

    except asyncio.TimeoutError:
        await message.reply("Filestorage2 на малинке недоступен (таймаут).")
    except aiohttp.ClientConnectorError:
        await message.reply("Filestorage2 на малинке недоступен (connection refused).")


@router.message(Command("wiki"))
async def cmd_wiki(message: Message) -> None:
    """Handle /wiki <query> — fetch Wikipedia article and save to marginalias."""
    import tempfile
    from datetime import datetime, timezone
    from urllib.parse import quote

    import aiohttp

    query = (message.text or "").split(maxsplit=1)[1].strip() if (message.text or "").strip().count(" ") >= 1 else ""
    if not query:
        await message.reply("Usage: /wiki <article name>")
        return

    MG_URL = "https://marginalias.net"
    MG_KEY = "sk-fs2-5cMnerTFUTuijez8YjQp8O1QnoDk4z2BfW8uLpyO3rlQ"
    AUTH_HEADER = {"Authorization": f"Bearer {MG_KEY}"}

    await message.reply(f"Ищу статью: {query}...")

    async with aiohttp.ClientSession() as http:
        # 1. Search Wikipedia for the article (try Russian first, then English)
        wiki_lang = "ru"
        api_url = (
            f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/"
            + quote(query, safe="")
        )
        async with http.get(api_url) as resp:
            if resp.status != 200:
                wiki_lang = "en"
                api_url = (
                    f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/"
                    + quote(query, safe="")
                )
                async with http.get(api_url) as resp2:
                    if resp2.status != 200:
                        await message.reply(f"Статья «{query}» не найдена в Wikipedia.")
                        return
                    summary_data = await resp2.json()
            else:
                summary_data = await resp.json()

        title = summary_data.get("title", query)
        page_url = summary_data.get("content_urls", {}).get("desktop", {}).get("page", "")

        # 2. Get full article HTML and convert to markdown-like text
        html_url = (
            f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/html/"
            + quote(title, safe="")
        )
        async with http.get(html_url) as resp:
            if resp.status == 200:
                html_content = await resp.text()
            else:
                html_content = ""

        # Simple HTML to text conversion (strip tags, keep structure)
        import html as html_module

        def html_to_markdown(raw_html: str) -> str:
            """Rough HTML→Markdown: headers, paragraphs, lists."""
            text = raw_html
            # Remove script/style
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
            # Headers
            for i in range(1, 7):
                text = re.sub(rf"<h{i}[^>]*>(.*?)</h{i}>", rf"\n{'#' * i} \1\n", text, flags=re.DOTALL | re.IGNORECASE)
            # List items
            text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL | re.IGNORECASE)
            # Paragraphs / line breaks
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
            # Bold/italic
            text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)
            # Strip remaining tags
            text = re.sub(r"<[^>]+>", "", text)
            # Decode entities
            text = html_module.unescape(text)
            # Collapse whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()

        article_md = html_to_markdown(html_content) if html_content else summary_data.get("extract", "")

        # Build final markdown document
        now = datetime.now(timezone.utc)
        doc = (
            f"# {title}\n\n"
            f"Source: {page_url}\n"
            f"Downloaded: {now.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"---\n\n"
            f"{article_md}\n"
        )

        # 3. Save to temp file and upload to marginalias
        filename = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") + ".md"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(doc)
            tmp_path = f.name

        try:
            # Upload file
            form = aiohttp.FormData()
            form.add_field(
                "file",
                open(tmp_path, "rb"),
                filename=filename,
                content_type="text/markdown",
            )
            form.add_field("description", f"Wikipedia: {title}")

            async with http.post(f"{MG_URL}/api/files", headers=AUTH_HEADER, data=form) as resp:
                if resp.status not in (200, 201):
                    err = await resp.text()
                    await message.reply(f"Ошибка загрузки на marginalias: {err}")
                    return
                file_data = await resp.json()

            file_id = file_data["id"]

            # 4. Create/find tags and apply them
            # Get all existing tags
            async with http.get(f"{MG_URL}/api/tags", headers=AUTH_HEADER) as resp:
                all_tags = await resp.json()

            tag_map = {t["name"]: t["id"] for t in all_tags}

            date_tag_name = f"d_{now.strftime('%Y%m%d%H%M')}"
            wiki_tag_name = "wiki"
            needed_tags = [date_tag_name, wiki_tag_name]
            tag_ids = []

            for tag_name in needed_tags:
                if tag_name in tag_map:
                    tag_ids.append(tag_map[tag_name])
                else:
                    # Create tag
                    async with http.post(
                        f"{MG_URL}/api/tags",
                        headers={**AUTH_HEADER, "Content-Type": "application/json"},
                        json={"name": tag_name},
                    ) as resp:
                        if resp.status in (200, 201):
                            new_tag = await resp.json()
                            tag_ids.append(new_tag["id"])

            # Apply tags to file
            if tag_ids:
                async with http.post(
                    f"{MG_URL}/api/files/{file_id}/tags",
                    headers={**AUTH_HEADER, "Content-Type": "application/json"},
                    json={"tag_ids": tag_ids},
                ) as resp:
                    pass  # best effort

            await message.reply(
                f"Сохранено: <b>{title}</b>\n"
                f"Файл: {MG_URL}/api/files/{file_id}/download\n"
                f"Теги: {', '.join(f'#{t}' for t in needed_tags)}",
                parse_mode=ParseMode.HTML,
            )
        finally:
            os.unlink(tmp_path)


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
