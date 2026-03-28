"""SQLite database: schema, initialization, queries."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     TEXT NOT NULL,
    user_id        INTEGER NOT NULL,
    request_number INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    message_id     INTEGER,
    status_msg_id  INTEGER,
    chat_id        INTEGER,
    created_at     TEXT NOT NULL,
    completed_at   TEXT,
    tokens_input   INTEGER DEFAULT 0,
    tokens_output  INTEGER DEFAULT 0,
    error_text     TEXT,
    UNIQUE(project_id, request_number)
);

CREATE TABLE IF NOT EXISTS interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  INTEGER NOT NULL REFERENCES requests(id),
    sub_number  INTEGER NOT NULL,
    type        TEXT NOT NULL,
    direction   TEXT NOT NULL,
    content     TEXT NOT NULL,
    message_id  INTEGER,
    created_at  TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db(path: Path | str = ":memory:") -> aiosqlite.Connection:
    """Open (or create) the database and ensure schema exists."""
    if isinstance(path, Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        db_path = str(path)
    else:
        db_path = path

    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.executescript(_SCHEMA)
    await db.commit()
    logger.info("Database initialized: %s", db_path)
    return db


# ── Requests ──────────────────────────────────────────────────────────────


async def create_request(
    db: aiosqlite.Connection,
    project_id: str,
    user_id: int,
    request_number: int,
    message_id: int,
    status_msg_id: int,
    chat_id: int,
) -> int:
    """Insert a new request row and return its id."""
    cursor = await db.execute(
        "INSERT INTO requests "
        "(project_id, user_id, request_number, message_id, status_msg_id, chat_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_id, user_id, request_number, message_id, status_msg_id, chat_id, _now()),
    )
    await db.commit()
    return cursor.lastrowid  # type: ignore[return-value]


async def update_request_status(
    db: aiosqlite.Connection,
    request_id: int,
    status: str,
    **kwargs: object,
) -> None:
    """Update status and optional extra fields on a request."""
    sets = ["status = ?"]
    values: list[object] = [status]

    if status in ("completed", "cancelled", "error"):
        sets.append("completed_at = ?")
        values.append(_now())

    for col in ("tokens_input", "tokens_output", "error_text"):
        if col in kwargs:
            sets.append(f"{col} = ?")
            values.append(kwargs[col])

    values.append(request_id)
    await db.execute(
        f"UPDATE requests SET {', '.join(sets)} WHERE id = ?",
        values,
    )
    await db.commit()


async def get_active_request(
    db: aiosqlite.Connection,
    project_id: str,
) -> aiosqlite.Row | None:
    """Return the currently running or awaiting request for a project."""
    cursor = await db.execute(
        "SELECT * FROM requests "
        "WHERE project_id = ? AND status IN ('pending', 'running', 'awaiting_input') "
        "ORDER BY id DESC LIMIT 1",
        (project_id,),
    )
    return await cursor.fetchone()


async def get_request_by_status_msg(
    db: aiosqlite.Connection,
    status_msg_id: int,
) -> aiosqlite.Row | None:
    """Find a request by its Telegram status message ID."""
    cursor = await db.execute(
        "SELECT * FROM requests WHERE status_msg_id = ?",
        (status_msg_id,),
    )
    return await cursor.fetchone()


async def get_recent_requests(
    db: aiosqlite.Connection,
    project_id: str,
    limit: int = 10,
) -> list[aiosqlite.Row]:
    """Return the latest N requests for a project."""
    cursor = await db.execute(
        "SELECT * FROM requests WHERE project_id = ? ORDER BY id DESC LIMIT ?",
        (project_id, limit),
    )
    return await cursor.fetchall()  # type: ignore[return-value]


async def get_token_totals(
    db: aiosqlite.Connection,
    project_id: str,
) -> dict:
    """Sum token usage across all requests for a project."""
    cursor = await db.execute(
        "SELECT COALESCE(SUM(tokens_input), 0) AS input, "
        "COALESCE(SUM(tokens_output), 0) AS output "
        "FROM requests WHERE project_id = ?",
        (project_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    return {
        "input": row["input"],
        "output": row["output"],
        "total": row["input"] + row["output"],
    }


# ── Interactions ──────────────────────────────────────────────────────────


async def create_interaction(
    db: aiosqlite.Connection,
    request_id: int,
    sub_number: int,
    type_: str,
    direction: str,
    content: str,
    message_id: int | None = None,
) -> int:
    """Insert an interaction row and return its id."""
    cursor = await db.execute(
        "INSERT INTO interactions "
        "(request_id, sub_number, type, direction, content, message_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (request_id, sub_number, type_, direction, content, message_id, _now()),
    )
    await db.commit()
    return cursor.lastrowid  # type: ignore[return-value]


async def get_interaction_by_message(
    db: aiosqlite.Connection,
    message_id: int,
) -> aiosqlite.Row | None:
    """Find an interaction by its Telegram message ID."""
    cursor = await db.execute(
        "SELECT * FROM interactions WHERE message_id = ?",
        (message_id,),
    )
    return await cursor.fetchone()


async def get_next_sub_number(
    db: aiosqlite.Connection,
    request_id: int,
) -> int:
    """Return the next sub_number for interactions within a request."""
    cursor = await db.execute(
        "SELECT COALESCE(MAX(sub_number), 0) + 1 FROM interactions WHERE request_id = ?",
        (request_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    return row[0]
