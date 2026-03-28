"""Telegram API retry wrapper with exponential backoff."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter

logger = logging.getLogger(__name__)

T = TypeVar("T")

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


async def telegram_retry(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = _MAX_RETRIES,
) -> T | None:
    """Execute a Telegram API call with retry logic.

    - TelegramRetryAfter: wait the specified time, then retry.
    - TelegramNetworkError: retry up to max_retries with exponential backoff.
    - Other exceptions: log and return None (don't crash the session).
    """
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except TelegramRetryAfter as e:
            logger.warning("Telegram rate limit, retrying after %s sec", e.retry_after)
            await asyncio.sleep(e.retry_after)
        except TelegramNetworkError:
            if attempt < max_retries:
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Telegram network error, retry %d/%d after %.1f sec",
                    attempt + 1, max_retries, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("Telegram network error after %d retries", max_retries)
                return None
        except Exception:
            logger.exception("Unexpected Telegram API error")
            return None
    return None
