"""Tests for SessionManager — orchestration of Claude process and Telegram bot."""

import asyncio
import json
import sys
import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pandemonium.tgbot.claude.process import ClaudeProcess
from pandemonium.tgbot.config import AppConfig
from pandemonium.tgbot.db import init_db
from pandemonium.tgbot.session.manager import SessionManager
from pandemonium.tgbot.session.state import SessionState
from pandemonium.tgbot.storage.protocol import ProtocolStorage


def _make_config(tmp_path) -> AppConfig:
    return AppConfig(
        telegram={"bot_token": "test"},
        allowed_users=[{"telegram_id": 111, "name": "Alice"}],
        projects=[{"id": "proj", "name": "Test", "path": str(tmp_path)}],
        storage={"base_path": str(tmp_path / "sessions")},
    )


def _mock_bot() -> MagicMock:
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=999))
    bot.send_document = AsyncMock()
    bot.send_chat_action = AsyncMock()
    bot.edit_message_text = AsyncMock()
    return bot


def _fake_claude_events(events: list[dict]) -> str:
    """Python script that prints events to stdout."""
    lines = json.dumps(events)
    return textwrap.dedent(f"""\
        import json, sys
        for e in json.loads('{lines}'):
            print(json.dumps(e), flush=True)
    """)


@pytest.fixture
async def setup(tmp_path):
    config = _make_config(tmp_path)
    db = await init_db(":memory:")
    storage = ProtocolStorage(tmp_path / "sessions")
    bot = _mock_bot()
    manager = SessionManager(config, db, storage, bot)
    yield manager, db, storage, bot, config, tmp_path
    await db.close()


async def test_create_request_basic(setup, monkeypatch):
    manager, db, storage, bot, config, tmp_path = setup

    events = [
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]},
        },
        {
            "type": "result",
            "result": "Done.",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
    ]
    script = _fake_claude_events(events)

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    req_number = await manager.create_request(
        project_id="proj",
        user_id=111,
        chat_id=500,
        message_id=1000,
        status_message_id=1001,
        prompt="say hello",
    )
    assert req_number == 1

    # Wait for background task to finish
    session = manager.active_session
    assert session is not None
    await session.process_task

    # Verify report was sent
    bot.send_document.assert_awaited()

    # Verify status message was updated
    bot.edit_message_text.assert_awaited()

    # Verify storage files
    req_dir = tmp_path / "sessions" / "proj" / "request_1"
    assert (req_dir / "request.md").exists()
    assert (req_dir / "report.md").exists()
    assert (req_dir / "meta.json").exists()


async def test_reject_concurrent_request(setup, monkeypatch):
    manager, *_ = setup

    # Fake a long-running process
    script = "import time; time.sleep(3600)"

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "first")

    with pytest.raises(RuntimeError, match="already in progress"):
        await manager.create_request("proj", 111, 500, 1002, 1003, "second")

    # Cleanup
    await manager.cancel_request(manager.active_session.request_id)


async def test_cancel_request(setup, monkeypatch):
    manager, db, storage, bot, config, tmp_path = setup

    script = "import time; time.sleep(3600)"

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "test")
    session = manager.active_session
    assert session is not None

    await manager.cancel_request(session.request_id)
    assert session.state == SessionState.CANCELLED

    # Wait for task cleanup
    await asyncio.sleep(0.2)


async def test_error_on_nonzero_exit(setup, monkeypatch):
    manager, db, storage, bot, config, tmp_path = setup

    # Script that exits with error
    script = "import sys; sys.exit(1)"

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "test")
    session = manager.active_session
    await session.process_task

    assert session.state == SessionState.ERROR
    bot.send_message.assert_awaited()  # Error message sent


async def test_permission_request_flow(setup, monkeypatch):
    """Permission request → user allows → session continues → result."""
    manager, db, storage, bot, config, tmp_path = setup

    # Script that emits: permission_request, then (after stdin) assistant + result
    script = textwrap.dedent("""\
        import json, sys
        # Emit permission request
        print(json.dumps({
            "type": "system", "subtype": "permission_request",
            "tool": "Bash", "description": "Run: ls"
        }), flush=True)
        # Wait for stdin response
        line = sys.stdin.readline()
        # Continue with result
        print(json.dumps({
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Listed files."}]}
        }), flush=True)
        print(json.dumps({
            "type": "result", "result": "Done.",
            "usage": {"input_tokens": 200, "output_tokens": 100}
        }), flush=True)
    """)

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "list files")
    session = manager.active_session

    # Wait for permission request to be sent
    await asyncio.sleep(0.3)
    assert session.state == SessionState.AWAITING_INPUT

    # Respond with Allow
    await manager.handle_permission_response(session.request_id, True)

    # Wait for completion
    await session.process_task

    assert session.state == SessionState.COMPLETED
    bot.send_document.assert_awaited()

    # Verify interaction was saved
    req_dir = tmp_path / "sessions" / "proj" / "request_1"
    assert (req_dir / "1.1.md").exists()
    assert (req_dir / "1.1.response.md").exists()


async def test_input_request_flow(setup, monkeypatch):
    """Input request → user replies → session continues → result."""
    manager, db, storage, bot, config, tmp_path = setup

    script = textwrap.dedent("""\
        import json, sys
        print(json.dumps({
            "type": "system", "subtype": "input_request",
            "question": "Which file?"
        }), flush=True)
        answer = sys.stdin.readline().strip()
        print(json.dumps({
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": f"Working on {answer}"}]}
        }), flush=True)
        print(json.dumps({
            "type": "result", "result": "Edited.",
            "usage": {"input_tokens": 300, "output_tokens": 150}
        }), flush=True)
    """)

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "edit file")
    session = manager.active_session

    await asyncio.sleep(0.3)
    assert session.state == SessionState.AWAITING_INPUT

    # Reply with file name
    await manager.handle_user_reply(session.request_id, "main.py")

    await session.process_task

    assert session.state == SessionState.COMPLETED

    # Check interaction files
    req_dir = tmp_path / "sessions" / "proj" / "request_1"
    assert (req_dir / "1.1.md").exists()
    assert (req_dir / "1.1.response.md").exists()
    assert (req_dir / "1.1.response.md").read_text() == "main.py"


async def test_cancel_during_awaiting_input(setup, monkeypatch):
    """Cancel while waiting for user input should work."""
    manager, db, storage, bot, config, tmp_path = setup

    script = textwrap.dedent("""\
        import json, sys
        print(json.dumps({
            "type": "system", "subtype": "input_request",
            "question": "Which file?"
        }), flush=True)
        sys.stdin.readline()  # block forever
    """)

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "test")
    session = manager.active_session

    await asyncio.sleep(0.3)
    assert session.state == SessionState.AWAITING_INPUT

    await manager.cancel_request(session.request_id)
    assert session.state == SessionState.CANCELLED

    await asyncio.sleep(0.3)


async def test_token_limit_exceeded(tmp_path, monkeypatch):
    """Token limit should stop the request."""
    config = AppConfig(
        telegram={"bot_token": "test"},
        allowed_users=[{"telegram_id": 111, "name": "Alice"}],
        projects=[{"id": "proj", "name": "Test", "path": str(tmp_path)}],
        storage={"base_path": str(tmp_path / "sessions")},
        token_budget={"per_request_limit": 100},  # very low limit
    )
    database = await init_db(":memory:")
    storage = ProtocolStorage(tmp_path / "sessions")
    bot = _mock_bot()
    manager = SessionManager(config, database, storage, bot)

    events = [
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]},
            "usage": {"input_tokens": 80, "output_tokens": 50},  # 130 > 100
        },
        {
            "type": "result",
            "result": "Done.",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
    ]
    script = _fake_claude_events(events)

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "test")
    session = manager.active_session
    await session.process_task

    assert session.state == SessionState.ERROR
    # Verify error message mentions token limit
    error_calls = [
        call for call in bot.send_message.call_args_list
        if "Token limit" in str(call)
    ]
    assert len(error_calls) > 0

    await database.close()


async def test_request_timeout(tmp_path, monkeypatch):
    """Request should be cancelled after timeout."""
    config = AppConfig(
        telegram={"bot_token": "test"},
        allowed_users=[{"telegram_id": 111, "name": "Alice"}],
        projects=[{"id": "proj", "name": "Test", "path": str(tmp_path)}],
        storage={"base_path": str(tmp_path / "sessions")},
        timeouts={"request_max_seconds": 1},  # 1 second timeout
    )
    database = await init_db(":memory:")
    storage = ProtocolStorage(tmp_path / "sessions")
    bot = _mock_bot()
    manager = SessionManager(config, database, storage, bot)

    # Script that runs forever
    script = "import time; time.sleep(3600)"

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "test")
    session = manager.active_session
    await session.process_task

    assert session.state == SessionState.ERROR

    await database.close()


async def test_shutdown(tmp_path, monkeypatch):
    """Shutdown should cancel active session and notify user."""
    config = AppConfig(
        telegram={"bot_token": "test"},
        allowed_users=[{"telegram_id": 111, "name": "Alice"}],
        projects=[{"id": "proj", "name": "Test", "path": str(tmp_path)}],
        storage={"base_path": str(tmp_path / "sessions")},
    )
    database = await init_db(":memory:")
    storage = ProtocolStorage(tmp_path / "sessions")
    bot = _mock_bot()
    manager = SessionManager(config, database, storage, bot)

    script = "import time; time.sleep(3600)"

    async def fake_start(self, prompt, project_path, **kwargs):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)

    await manager.create_request("proj", 111, 500, 1000, 1001, "test")

    await manager.shutdown()
    assert manager.is_shutting_down

    # New requests should be rejected
    with pytest.raises(RuntimeError, match="shutting down"):
        await manager.create_request("proj", 111, 500, 1002, 1003, "another")

    await asyncio.sleep(0.3)
    await database.close()
