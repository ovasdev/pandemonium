"""Claude Code subprocess management."""

import asyncio
import logging
import os
import signal
from collections.abc import AsyncIterator
from pathlib import Path

from pandemonium.tgbot.claude.events import parse_event
from pandemonium.tgbot.claude.types import ClaudeEvent

logger = logging.getLogger(__name__)

_CANCEL_TIMEOUT = 5  # seconds between SIGTERM and SIGKILL

# Claude Code stream-json can emit very long lines (e.g. base64-encoded images).
# Default asyncio StreamReader limit is 64 KiB — raise to 16 MiB.
_STREAM_LIMIT = 16 * 1024 * 1024

# Env vars that prevent child Claude Code from starting
_CLAUDE_ENV_VARS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")


class ClaudeProcess:
    """Manages a single Claude Code child process."""

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._stderr_buffer: list[str] = []

    async def start(
        self,
        prompt: str,
        project_path: Path,
        *,
        resume_session_id: str | None = None,
        extra_env: dict[str, str] | None = None,
        append_system_prompt: str | None = None,
    ) -> None:
        """Launch Claude Code with the given prompt.

        If *resume_session_id* is provided, the conversation is resumed
        within the same Claude Code session (preserves context).

        *extra_env* — additional environment variables passed to the child process.
        *append_system_prompt* — text appended to the system prompt via CLI flag.
        """
        logger.info(
            "Starting Claude Code in %s (resume=%s)", project_path, resume_session_id,
        )
        self._stderr_buffer.clear()

        # Clean env so child Claude doesn't think it's nested
        env = {k: v for k, v in os.environ.items() if k not in _CLAUDE_ENV_VARS}
        if extra_env:
            env.update(extra_env)

        cmd: list[str] = [
            "claude",
            "--print",
            "--output-format", "stream-json",
            "--verbose",
            "--max-turns", "50",
            "--permission-mode", "bypassPermissions",
        ]
        if resume_session_id:
            cmd += ["--resume", resume_session_id]
        if append_system_prompt:
            cmd += ["--append-system-prompt", append_system_prompt]
        cmd.append(prompt)

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project_path),
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=_STREAM_LIMIT,
        )
        # Start background stderr reader
        asyncio.create_task(self._read_stderr())

    async def _read_stderr(self) -> None:
        """Collect stderr output for diagnostics."""
        assert self._process and self._process.stderr
        try:
            async for raw_line in self._process.stderr:
                line = raw_line.decode(errors="replace").rstrip()
                if line:
                    self._stderr_buffer.append(line)
                    logger.debug("Claude stderr: %s", line)
        except Exception:
            pass

    async def stream_events(self) -> AsyncIterator[ClaudeEvent]:
        """Yield parsed events from Claude Code stdout."""
        assert self._process and self._process.stdout
        async for raw_line in self._process.stdout:
            line = raw_line.decode(errors="replace")
            event = parse_event(line)
            if event is not None:
                yield event

    async def send_input(self, text: str) -> None:
        """Send text to Claude Code stdin (no-op when stdin is DEVNULL)."""
        if not self._process or not self._process.stdin:
            logger.warning("Cannot send input: stdin not available")
            return
        data = (text + "\n").encode()
        self._process.stdin.write(data)
        await self._process.stdin.drain()

    async def send_permission(self, allowed: bool) -> None:
        """Send a permission response via stdin (no-op when stdin is DEVNULL)."""
        import json
        payload = json.dumps({"type": "permission", "allowed": allowed})
        await self.send_input(payload)

    async def cancel(self) -> None:
        """Gracefully stop the process: SIGTERM, wait, then SIGKILL."""
        if not self.is_running():
            return
        assert self._process

        logger.info("Cancelling Claude Code process (pid=%s)", self._process.pid)
        try:
            self._process.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            return

        try:
            await asyncio.wait_for(self._process.wait(), timeout=_CANCEL_TIMEOUT)
        except TimeoutError:
            logger.warning("Claude Code did not exit after SIGTERM, sending SIGKILL")
            try:
                self._process.kill()
            except ProcessLookupError:
                pass
            await self._process.wait()

    async def wait(self) -> int:
        """Wait for the process to finish and return exit code."""
        assert self._process
        return await self._process.wait()

    def is_running(self) -> bool:
        """Check if the process is still alive."""
        return self._process is not None and self._process.returncode is None

    @property
    def stderr_output(self) -> str:
        """Collected stderr output for diagnostics."""
        return "\n".join(self._stderr_buffer)
