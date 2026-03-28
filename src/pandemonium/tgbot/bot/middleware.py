"""Authorization middleware — whitelist check by Telegram user ID."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Reject events from users not in the allowed set."""

    def __init__(self, allowed_ids: set[int]) -> None:
        self.allowed_ids = allowed_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user and user.id not in self.allowed_ids:
            logger.warning("Unauthorized access from user %s", user.id)
            # In group chats — silently ignore unauthorized users
            if isinstance(event, Message) and event.chat.type in ("group", "supergroup"):
                return None
            if isinstance(event, Message):
                await event.answer("Access denied.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Access denied.", show_alert=True)
            return None
        return await handler(event, data)
