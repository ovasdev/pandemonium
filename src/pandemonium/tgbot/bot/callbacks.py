"""Inline button callback handlers (Cancel, Allow/Deny, Project switch)."""

import logging

from aiogram import F, Router
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
    """Handle persona selection — only works for the default project."""
    persona_name = (callback.data or "").split(":", 1)[1]

    # Personas only work in the default project
    default_project = config.default_project
    if session_manager.active_project_id != default_project.id:
        await callback.answer("Personas only available in the default project.")
        return

    # Verify persona exists on disk
    personas = scan_personas(default_project.path)
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
