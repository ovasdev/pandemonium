"""Tests for ClaudeProcess — uses a fake subprocess to avoid real Claude Code."""

import asyncio
import json
import sys
import textwrap

import pytest

from pandemonium.tgbot.claude.process import ClaudeProcess
from pandemonium.tgbot.claude.types import AssistantEvent, ResultEvent, SystemEvent


def _fake_claude_script(events: list[dict]) -> str:
    """Generate a Python script that prints JSON events to stdout."""
    lines = json.dumps(events)
    return textwrap.dedent(f"""\
        import json, sys
        events = json.loads('{lines}')
        for e in events:
            print(json.dumps(e), flush=True)
    """)


def _make_process(monkeypatch, events: list[dict]) -> ClaudeProcess:
    """Create a ClaudeProcess that runs a fake script instead of claude CLI."""
    script = _fake_claude_script(events)

    async def fake_start(self, prompt, project_path):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)
    return ClaudeProcess()


@pytest.fixture
def sample_events():
    return [
        {"type": "system", "subtype": "init", "session_id": "test-session"},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Hello!"}],
            },
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
        {
            "type": "result",
            "result": "Done.",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "is_error": False,
        },
    ]


async def test_stream_events(monkeypatch, sample_events, tmp_path):
    proc = _make_process(monkeypatch, sample_events)
    await proc.start("test", tmp_path)

    events = []
    async for event in proc.stream_events():
        events.append(event)

    assert len(events) == 3
    assert isinstance(events[0], SystemEvent)
    assert isinstance(events[1], AssistantEvent)
    assert events[1].text == "Hello!"
    assert isinstance(events[2], ResultEvent)
    assert events[2].text == "Done."

    code = await proc.wait()
    assert code == 0


async def test_is_running(monkeypatch, sample_events, tmp_path):
    proc = _make_process(monkeypatch, sample_events)
    assert not proc.is_running()

    await proc.start("test", tmp_path)
    assert proc.is_running()

    # Consume all output so process finishes
    async for _ in proc.stream_events():
        pass
    await proc.wait()
    assert not proc.is_running()


async def test_cancel(monkeypatch, tmp_path):
    """Test cancellation of a long-running process."""
    # Script that sleeps forever
    script = "import time; time.sleep(3600)"

    async def fake_start(self, prompt, project_path):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)
    proc = ClaudeProcess()
    await proc.start("test", tmp_path)

    assert proc.is_running()
    await proc.cancel()
    assert not proc.is_running()


async def test_cancel_already_finished(monkeypatch, sample_events, tmp_path):
    """Cancel on an already-exited process should be a no-op."""
    proc = _make_process(monkeypatch, sample_events)
    await proc.start("test", tmp_path)
    async for _ in proc.stream_events():
        pass
    await proc.wait()

    # Should not raise
    await proc.cancel()


async def test_stderr_collection(monkeypatch, tmp_path):
    """Stderr output should be collected."""
    script = "import sys; sys.stderr.write('debug info\\n'); sys.stderr.flush()"

    async def fake_start(self, prompt, project_path):
        self._stderr_buffer.clear()
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_stderr())

    monkeypatch.setattr(ClaudeProcess, "start", fake_start)
    proc = ClaudeProcess()
    await proc.start("test", tmp_path)
    await proc.wait()

    # Give stderr reader a moment to finish
    await asyncio.sleep(0.1)
    assert "debug info" in proc.stderr_output
