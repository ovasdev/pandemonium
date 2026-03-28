"""Tests for Telegram API retry logic."""

from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter

from pandemonium.tgbot.bot.retry import telegram_retry

_FAKE_METHOD = MagicMock()


def _network_error() -> TelegramNetworkError:
    return TelegramNetworkError(method=_FAKE_METHOD, message="err")


def _retry_after_error(seconds: float = 0.01) -> TelegramRetryAfter:
    return TelegramRetryAfter(
        method=_FAKE_METHOD, message="rate limit", retry_after=int(seconds),
    )


async def test_retry_success():
    fn = AsyncMock(return_value="ok")
    result = await telegram_retry(fn)
    assert result == "ok"
    fn.assert_awaited_once()


async def test_retry_on_network_error():
    fn = AsyncMock(side_effect=[_network_error(), "ok"])
    result = await telegram_retry(fn, max_retries=3)
    assert result == "ok"
    assert fn.await_count == 2


async def test_retry_exhausted():
    fn = AsyncMock(side_effect=[_network_error(), _network_error(), _network_error()])
    result = await telegram_retry(fn, max_retries=2)
    assert result is None
    assert fn.await_count == 3  # initial + 2 retries


async def test_retry_after():
    fn = AsyncMock(side_effect=[_retry_after_error(0), "ok"])
    result = await telegram_retry(fn)
    assert result == "ok"


async def test_unexpected_error():
    fn = AsyncMock(side_effect=ValueError("boom"))
    result = await telegram_retry(fn)
    assert result is None
