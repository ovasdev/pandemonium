"""Tests for StreamBuffer — debounced text flushing."""

import asyncio

import pytest

from pandemonium.tgbot.session.buffer import StreamBuffer


@pytest.fixture
def collector():
    """Collects flushed text chunks."""
    chunks: list[str] = []

    async def callback(text: str) -> None:
        chunks.append(text)

    return chunks, callback


async def test_flush_on_close(collector):
    chunks, cb = collector
    buf = StreamBuffer(cb, interval=10)  # long interval — won't trigger
    await buf.append("hello")
    await buf.close()
    assert chunks == ["hello"]


async def test_flush_on_max_size(collector):
    chunks, cb = collector
    buf = StreamBuffer(cb, interval=10, max_size=10)
    await buf.append("x" * 15)  # over max_size
    assert len(chunks) == 1
    assert chunks[0] == "x" * 15
    await buf.close()


async def test_debounce_timer(collector):
    chunks, cb = collector
    buf = StreamBuffer(cb, interval=0.1, max_size=10000)
    await buf.append("a")
    await buf.append("b")
    # Wait for debounce timer
    await asyncio.sleep(0.2)
    assert chunks == ["ab"]
    await buf.close()


async def test_accumulates_before_flush(collector):
    chunks, cb = collector
    buf = StreamBuffer(cb, interval=10, max_size=10000)
    await buf.append("one ")
    await buf.append("two ")
    await buf.append("three")
    await buf.close()
    assert chunks == ["one two three"]


async def test_multiple_flushes(collector):
    chunks, cb = collector
    buf = StreamBuffer(cb, interval=10, max_size=5)
    await buf.append("12345")  # exactly max — triggers
    await buf.append("abc")
    await buf.close()
    assert len(chunks) == 2
    assert chunks[0] == "12345"
    assert chunks[1] == "abc"


async def test_close_empty_buffer(collector):
    chunks, cb = collector
    buf = StreamBuffer(cb, interval=10)
    await buf.close()
    assert chunks == []


async def test_flush_callback_error(caplog):
    """Errors in flush callback should not crash the buffer."""
    async def bad_callback(text: str) -> None:
        raise RuntimeError("send failed")

    buf = StreamBuffer(bad_callback, interval=10)
    await buf.append("test")
    await buf.close()  # should not raise
