"""Tests for /status, /history, /tokens formatters and recovery."""

import pytest

from pandemonium.tgbot.bot.formatters import (
    format_active_status,
    format_history,
    format_tokens,
)
from pandemonium.tgbot.db import create_request, init_db, update_request_status
from pandemonium.tgbot.main import _recover_interrupted_requests
from pandemonium.tgbot.storage.protocol import ProtocolStorage


def test_format_history_empty():
    assert format_history([]) == "No requests yet."


def test_format_history_with_rows():
    # Simulate Row-like dicts
    class FakeRow(dict):
        def __getitem__(self, key):
            return dict.__getitem__(self, key)

    rows = [
        FakeRow(request_number=3, status="completed", created_at="2026-03-10T12:00:00Z", tokens_input=100, tokens_output=50),
        FakeRow(request_number=2, status="error", created_at="2026-03-09T10:00:00Z", tokens_input=30, tokens_output=20),
    ]
    result = format_history(rows)
    assert "#3" in result
    assert "completed" in result
    assert "150" in result
    assert "#2" in result
    assert "error" in result


def test_format_tokens():
    result = format_tokens("my-app", 12, {"input": 180000, "output": 65000, "total": 245000})
    assert "my-app" in result
    assert "12" in result
    assert "245,000" in result


def test_format_active_status():
    result = format_active_status(5, "2026-03-10T12:00:00+00:00")
    assert "#5" in result
    assert "running" in result


# ── Recovery ──────────────────────────────────────────────────────────────


async def test_recover_interrupted_requests(tmp_path):
    db = await init_db(":memory:")
    storage = ProtocolStorage(tmp_path)

    rid1 = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    await update_request_status(db, rid1, "running")
    rid2 = await create_request(db, "proj", 111, 2, 1002, 1003, 500)
    await update_request_status(db, rid2, "completed")

    await _recover_interrupted_requests(db, storage)

    cursor = await db.execute("SELECT status FROM requests WHERE id = ?", (rid1,))
    row = await cursor.fetchone()
    assert row["status"] == "error"

    cursor = await db.execute("SELECT status FROM requests WHERE id = ?", (rid2,))
    row = await cursor.fetchone()
    assert row["status"] == "completed"  # not affected

    assert (tmp_path / "proj" / "request_1" / "error.md").exists()

    await db.close()
