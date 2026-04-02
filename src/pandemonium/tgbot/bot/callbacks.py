"""Inline button callback handlers (Cancel, Allow/Deny, Project switch, Quantum dice)."""

import asyncio
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from pandemonium.tgbot.config import AppConfig, scan_personas
from pandemonium.tgbot.session.manager import SessionManager
from pandemonium.tgbot.session.state import SessionState

logger = logging.getLogger(__name__)

router = Router(name="callbacks")


@router.callback_query(F.data.startswith("cancel:"))
async def on_cancel(callback: CallbackQuery, session_manager: SessionManager) -> None:
    """Handle Cancel button press."""
    try:
        request_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    except (ValueError, IndexError):
        await callback.answer("Invalid action.")
        return

    await session_manager.cancel_request(request_id)
    await callback.answer("Cancelling...")


@router.callback_query(F.data.startswith("perm:"))
async def on_permission(callback: CallbackQuery, session_manager: SessionManager) -> None:
    """Handle Allow/Deny button press for permission requests."""
    try:
        parts = callback.data.split(":")  # type: ignore[union-attr]
        request_id = int(parts[1])
        action = parts[2]  # "allow" or "deny"
    except (ValueError, IndexError):
        await callback.answer("Invalid action.")
        return

    allowed = action == "allow"
    await session_manager.handle_permission_response(request_id, allowed)

    # Update the message to show the user's choice
    label = "Allowed" if allowed else "Denied"
    try:
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            original_text = callback.message.text or ""
            await callback.message.edit_text(f"{original_text}\n\n→ {label}")
    except Exception:
        logger.debug("Could not update permission message", exc_info=True)

    await callback.answer(label)


@router.callback_query(F.data.startswith("project:"))
async def on_project_switch(
    callback: CallbackQuery,
    config: AppConfig,
    session_manager: SessionManager,
) -> None:
    """Handle project selection button — switch active project without LLM."""
    project_id = (callback.data or "").split(":", 1)[1]
    project = config.get_project(project_id)
    if not project:
        await callback.answer("Unknown project.")
        return

    if project_id == session_manager.active_project_id:
        await callback.answer(f"Already active: {project.name}")
        return

    active = session_manager.active_session
    if active and active.state not in (SessionState.IDLE, SessionState.COMPLETED, SessionState.CANCELLED, SessionState.ERROR):
        await callback.answer("Cannot switch while a request is running.")
        return

    session_manager.set_active_project(project_id)

    # Update the keyboard to reflect new active project
    buttons: list[list[InlineKeyboardButton]] = []
    for p in config.projects:
        label = f"{'✦ ' if p.id == project_id else ''}{p.name}"
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"project:{p.id}"),
        ])
    try:
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            )
    except Exception:
        logger.debug("Could not update project keyboard", exc_info=True)

    await callback.answer(f"Switched to {project.name}")


_QRAND_SCRIPT = Path(__file__).resolve().parents[4] / ".pandemonium" / "tools" / "quantum_random.sh"


@router.callback_query(F.data.startswith("qrand:"))
async def on_qrand(callback: CallbackQuery) -> None:
    """Handle quantum dice button press — roll and reply."""
    try:
        parts = (callback.data or "").split(":")
        count, from_val, to_val = int(parts[1]), int(parts[2]), int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("Invalid action.")
        return

    proc = await asyncio.create_subprocess_exec(
        str(_QRAND_SCRIPT), str(count), str(from_val), str(to_val),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    except TimeoutError:
        proc.kill()
        await callback.answer("Квантовая кость недоступна.")
        return

    if proc.returncode != 0:
        await callback.answer("Квантовая кость недоступна.")
        return

    result = stdout.decode().strip()
    sides = to_val - from_val + 1
    text = f"🎲 d{sides} → <b>{result}</b>"

    # Highlight the pressed button, keep all buttons active for re-rolls
    if callback.message and callback.message.reply_markup:
        new_rows: list[list[InlineKeyboardButton]] = []
        for row in callback.message.reply_markup.inline_keyboard:
            new_row: list[InlineKeyboardButton] = []
            for btn in row:
                label = btn.text.lstrip("▸ ") if btn.text.startswith("▸ ") else btn.text
                if btn.callback_data == callback.data:
                    label = f"▸ {label}"
                new_row.append(InlineKeyboardButton(
                    text=label,
                    callback_data=btn.callback_data,
                ))
            new_rows.append(new_row)
        try:
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_rows),
            )
        except Exception:
            logger.debug("Could not update dice buttons", exc_info=True)

    if callback.message:
        await callback.message.reply(text, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery) -> None:
    """Ignore clicks on non-interactive header buttons."""
    await callback.answer()


@router.callback_query(F.data.startswith("persona:"))
async def on_persona_switch(
    callback: CallbackQuery,
    config: AppConfig,
    session_manager: SessionManager,
) -> None:
    """Handle persona selection for the currently active project."""
    persona_name = (callback.data or "").split(":", 1)[1]

    # Get the active project
    active_project = config.get_project(session_manager.active_project_id) or config.default_project

    # Verify persona exists on disk
    personas = scan_personas(active_project.path)
    if persona_name not in personas:
        await callback.answer("Unknown persona.")
        return

    active = session_manager.active_session
    if active and active.state not in (
        SessionState.IDLE, SessionState.COMPLETED,
        SessionState.CANCELLED, SessionState.ERROR,
    ):
        await callback.answer("Cannot switch while a request is running.")
        return

    session_manager.set_active_persona(persona_name)

    # Update keyboard to reflect new active persona
    buttons: list[list[InlineKeyboardButton]] = []
    for name in personas:
        marker = "✦ " if name == persona_name else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{marker}{name}",
                callback_data=f"persona:{name}",
            ),
        ])

    try:
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            )
    except Exception:
        logger.debug("Could not update persona keyboard", exc_info=True)

    await callback.answer(f"Switched to {persona_name}")
