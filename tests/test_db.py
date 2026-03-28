"""Tests for database initialization, schema, and query functions."""

import pytest

from pandemonium.tgbot.db import (
    create_interaction,
    create_request,
    get_active_request,
    get_interaction_by_message,
    get_next_sub_number,
    get_recent_requests,
    get_request_by_status_msg,
    get_token_totals,
    init_db,
    update_request_status,
)


@pytest.fixture
async def db():
    conn = await init_db(":memory:")
    yield conn
    await conn.close()


# ── Schema tests ──────────────────────────────────────────────────────────


async def test_tables_exist(db):
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in await cursor.fetchall()]
    assert "requests" in tables
    assert "interactions" in tables


async def test_requests_columns(db):
    cursor = await db.execute("PRAGMA table_info(requests)")
    columns = {row[1] for row in await cursor.fetchall()}
    expected = {
        "id", "project_id", "user_id", "request_number", "status",
        "message_id", "status_msg_id", "chat_id", "created_at",
        "completed_at", "tokens_input", "tokens_output", "error_text",
    }
    assert expected == columns


async def test_interactions_columns(db):
    cursor = await db.execute("PRAGMA table_info(interactions)")
    columns = {row[1] for row in await cursor.fetchall()}
    expected = {
        "id", "request_id", "sub_number", "type", "direction",
        "content", "message_id", "created_at",
    }
    assert expected == columns


async def test_unique_constraint(db):
    await db.execute(
        "INSERT INTO requests (project_id, user_id, request_number, created_at) "
        "VALUES ('proj', 1, 1, '2026-01-01T00:00:00Z')"
    )
    await db.commit()

    with pytest.raises(Exception):
        await db.execute(
            "INSERT INTO requests (project_id, user_id, request_number, created_at) "
            "VALUES ('proj', 1, 1, '2026-01-01T00:00:00Z')"
        )


async def test_init_db_file(tmp_path):
    db_path = tmp_path / "data" / "pandemonium.db"
    conn = await init_db(db_path)
    assert db_path.exists()
    await conn.close()


# ── Request CRUD ──────────────────────────────────────────────────────────


async def test_create_request(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    assert rid == 1

    cursor = await db.execute("SELECT * FROM requests WHERE id = ?", (rid,))
    row = await cursor.fetchone()
    assert row["project_id"] == "proj"
    assert row["status"] == "pending"


async def test_update_request_status(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    await update_request_status(db, rid, "running")

    cursor = await db.execute("SELECT status FROM requests WHERE id = ?", (rid,))
    row = await cursor.fetchone()
    assert row["status"] == "running"


async def test_update_request_completed(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    await update_request_status(
        db, rid, "completed", tokens_input=500, tokens_output=100,
    )

    cursor = await db.execute("SELECT * FROM requests WHERE id = ?", (rid,))
    row = await cursor.fetchone()
    assert row["status"] == "completed"
    assert row["completed_at"] is not None
    assert row["tokens_input"] == 500
    assert row["tokens_output"] == 100


async def test_update_request_error(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    await update_request_status(db, rid, "error", error_text="Process crashed")

    cursor = await db.execute("SELECT * FROM requests WHERE id = ?", (rid,))
    row = await cursor.fetchone()
    assert row["error_text"] == "Process crashed"
    assert row["completed_at"] is not None


async def test_get_active_request(db):
    await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    rid2 = await create_request(db, "proj", 111, 2, 1002, 1003, 500)
    await update_request_status(db, 1, "completed")
    await update_request_status(db, rid2, "running")

    row = await get_active_request(db, "proj")
    assert row is not None
    assert row["id"] == rid2


async def test_get_active_request_none(db):
    await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    await update_request_status(db, 1, "completed")

    assert await get_active_request(db, "proj") is None


async def test_get_request_by_status_msg(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    row = await get_request_by_status_msg(db, 1001)
    assert row is not None
    assert row["id"] == rid

    assert await get_request_by_status_msg(db, 9999) is None


async def test_get_recent_requests(db):
    for i in range(1, 6):
        await create_request(db, "proj", 111, i, 1000 + i, 2000 + i, 500)
    rows = await get_recent_requests(db, "proj", limit=3)
    assert len(rows) == 3
    assert rows[0]["request_number"] == 5  # most recent first


async def test_get_token_totals(db):
    rid1 = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    rid2 = await create_request(db, "proj", 111, 2, 1002, 1003, 500)
    await update_request_status(db, rid1, "completed", tokens_input=100, tokens_output=50)
    await update_request_status(db, rid2, "completed", tokens_input=200, tokens_output=80)

    totals = await get_token_totals(db, "proj")
    assert totals == {"input": 300, "output": 130, "total": 430}


async def test_get_token_totals_empty(db):
    totals = await get_token_totals(db, "proj")
    assert totals == {"input": 0, "output": 0, "total": 0}


# ── Interactions ──────────────────────────────────────────────────────────


async def test_create_interaction(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    iid = await create_interaction(db, rid, 1, "question", "from_claude", "What file?", 2000)
    assert iid == 1

    cursor = await db.execute("SELECT * FROM interactions WHERE id = ?", (iid,))
    row = await cursor.fetchone()
    assert row["type"] == "question"
    assert row["direction"] == "from_claude"


async def test_get_interaction_by_message(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    await create_interaction(db, rid, 1, "question", "from_claude", "What?", 2000)

    row = await get_interaction_by_message(db, 2000)
    assert row is not None
    assert row["content"] == "What?"

    assert await get_interaction_by_message(db, 9999) is None


async def test_get_next_sub_number(db):
    rid = await create_request(db, "proj", 111, 1, 1000, 1001, 500)
    assert await get_next_sub_number(db, rid) == 1

    await create_interaction(db, rid, 1, "question", "from_claude", "Q1")
    assert await get_next_sub_number(db, rid) == 2

    await create_interaction(db, rid, 2, "question", "from_claude", "Q2")
    assert await get_next_sub_number(db, rid) == 3
