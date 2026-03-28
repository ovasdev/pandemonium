"""Stream buffer with debounced flushing for Telegram output."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class StreamBuffer:
    """Accumulates text chunks and flushes them with debounce."""

    def __init__(
        self,
        flush_callback: Callable[[str], Awaitable[None]],
        interval: float = 2.5,
        max_size: int = 3500,
    ) -> None:
        self._flush_callback = flush_callback
        self._interval = interval
        self._max_size = max_size
        self._buffer: list[str] = []
        self._current_size = 0
        self._timer: asyncio.Task | None = None

    async def append(self, text: str) -> None:
        """Add text to the buffer; flush immediately if over max_size."""
        self._buffer.append(text)
        self._current_size += len(text)

        if self._current_size >= self._max_size:
            await self.flush()
        else:
            self._restart_timer()

    async def flush(self) -> None:
        """Send accumulated buffer content via callback."""
        self._cancel_timer()
        if not self._buffer:
            return
        text = "".join(self._buffer)
        self._buffer.clear()
        self._current_size = 0
        try:
            await self._flush_callback(text)
        except Exception:
            logger.exception("Error in flush callback")

    async def close(self) -> None:
        """Flush remaining content and stop the timer."""
        await self.flush()

    def _restart_timer(self) -> None:
        self._cancel_timer()
        self._timer = asyncio.create_task(self._timer_tick())

    def _cancel_timer(self) -> None:
        if self._timer and not self._timer.done():
            self._timer.cancel()
            self._timer = None

    async def _timer_tick(self) -> None:
        try:
            await asyncio.sleep(self._interval)
            await self.flush()
        except asyncio.CancelledError:
            pass
