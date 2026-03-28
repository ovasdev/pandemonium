"""Tests for bot handlers and middleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pandemonium.tgbot.bot.formatters import welcome_message
from pandemonium.tgbot.bot.middleware import AuthMiddleware


def test_welcome_message():
    msg = welcome_message("Alice", "My App")
    assert "Alice" in msg
    assert "My App" in msg


@pytest.fixture
def auth_middleware():
    return AuthMiddleware(allowed_ids={111, 222})


async def test_auth_allows_whitelisted(auth_middleware):
    handler = AsyncMock(return_value="ok")
    user = MagicMock()
    user.id = 111
    event = MagicMock()
    data = {"event_from_user": user}

    result = await auth_middleware(handler, event, data)
    assert result == "ok"
    handler.assert_awaited_once()


async def test_auth_blocks_unknown_user(auth_middleware):
    handler = AsyncMock()
    user = MagicMock()
    user.id = 999

    # Simulate a Message event in a private chat
    from aiogram.types import Message
    event = MagicMock(spec=Message)
    event.answer = AsyncMock()
    chat = MagicMock()
    chat.type = "private"
    event.chat = chat
    data = {"event_from_user": user}

    result = await auth_middleware(handler, event, data)
    assert result is None
    handler.assert_not_awaited()
    event.answer.assert_awaited_once_with("Access denied.")


async def test_auth_no_user_passes_through(auth_middleware):
    handler = AsyncMock(return_value="ok")
    event = MagicMock()
    data = {}

    result = await auth_middleware(handler, event, data)
    assert result == "ok"


async def test_auth_silent_in_group_chat(auth_middleware):
    """In group chats, unauthorized users are silently ignored (no 'Access denied')."""
    handler = AsyncMock()
    user = MagicMock()
    user.id = 999

    from aiogram.types import Message
    event = MagicMock(spec=Message)
    event.answer = AsyncMock()
    chat = MagicMock()
    chat.type = "supergroup"
    event.chat = chat
    data = {"event_from_user": user}

    result = await auth_middleware(handler, event, data)
    assert result is None
    handler.assert_not_awaited()
    event.answer.assert_not_awaited()


# ── Group mention helpers ─────────────────────────────────────────────

from pandemonium.tgbot.bot.handlers import _is_bot_mentioned, _strip_mention


def test_is_bot_mentioned_positive():
    msg = MagicMock()
    msg.text = "Привет @MyBot расскажи про архитектуру"
    msg.caption = None
    assert _is_bot_mentioned(msg, "MyBot") is True


def test_is_bot_mentioned_case_insensitive():
    msg = MagicMock()
    msg.text = "Привет @mybot расскажи"
    msg.caption = None
    assert _is_bot_mentioned(msg, "MyBot") is True


def test_is_bot_mentioned_negative():
    msg = MagicMock()
    msg.text = "Просто сообщение без упоминания"
    msg.caption = None
    assert _is_bot_mentioned(msg, "MyBot") is False


def test_is_bot_mentioned_in_caption():
    msg = MagicMock()
    msg.text = None
    msg.caption = "Файл для @MyBot"
    assert _is_bot_mentioned(msg, "MyBot") is True


def test_strip_mention():
    assert _strip_mention("@MyBot расскажи про X", "MyBot") == "расскажи про X"
    assert _strip_mention("Привет @MyBot расскажи", "MyBot") == "Привет расскажи"
    assert _strip_mention("текст без бота", "MyBot") == "текст без бота"


def test_strip_mention_multiple():
    assert _strip_mention("@MyBot @MyBot hello", "MyBot") == "hello"
