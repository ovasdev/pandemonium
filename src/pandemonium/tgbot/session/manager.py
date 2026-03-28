"""Session manager — coordinates Claude process, Telegram bot, DB, and storage."""

import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

import pandemonium.tgbot.db as db
from pandemonium.tgbot.bot.retry import telegram_retry
from pandemonium.tgbot.claude.process import ClaudeProcess
from pandemonium.tgbot.claude.types import (
    AssistantEvent,
    InputRequestEvent,
    PermissionRequestEvent,
    ResultEvent,
    SystemEvent,
    ToolUseEvent,
)
from pandemonium.tgbot.bot.markup import md_to_telegram_html, truncate_html
from pandemonium.tgbot.config import AppConfig
from pandemonium.tgbot.session.buffer import StreamBuffer
from pandemonium.tgbot.session.state import ActiveSession, SessionState
from pandemonium.tgbot.storage.protocol import ProtocolStorage

logger = logging.getLogger(__name__)


class SessionManager:
    """One instance per application. Manages the active session."""

    def __init__(
        self,
        config: AppConfig,
        database: "aiosqlite.Connection",
        storage: ProtocolStorage,
        bot: Bot,
    ) -> None:
        self._config = config
        self._db = database
        self._storage = storage
        self._bot = bot
        self._active: ActiveSession | None = None
        self._shutting_down = False
        # Resume ID for the *next* Claude Code request (set after init event).
        # Cleared on project/persona switch to force fresh context.
        self._next_resume_id: str | None = None
        # Active project and persona (persist across requests)
        self._active_project_id: str = config.default_project.id
        self._active_persona: str | None = None

    @property
    def active_session(self) -> ActiveSession | None:
        return self._active

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    @property
    def claude_session_id(self) -> str | None:
        return self._next_resume_id

    @property
    def active_project_id(self) -> str:
        return self._active_project_id

    @property
    def active_persona(self) -> str | None:
        return self._active_persona

    def update_config(self, config: AppConfig) -> None:
        """Hot-reload config (e.g. after config.yaml change)."""
        self._config = config
        logger.info("Config updated in SessionManager")

    def set_active_project(self, project_id: str) -> None:
        """Switch the active project. Resets persona and session for fresh context."""
        project = self._config.get_project(project_id)
        if project is None:
            raise ValueError(f"Unknown project: {project_id}")
        self._active_project_id = project_id
        self._active_persona = None
        self._next_resume_id = None
        logger.info("Switched active project to %s (%s)", project_id, project.path)

    def set_active_persona(self, persona: str | None) -> None:
        """Set the active persona name. Only for default project. Clears session."""
        self._active_persona = persona
        self._next_resume_id = None
        logger.info("Active persona: %s (session cleared)", persona or "(none)")

    def clear_session(self) -> None:
        """Clear the Claude Code session ID, starting a fresh conversation next time."""
        self._next_resume_id = None
        logger.info("Claude session cleared")

    async def create_request(
        self,
        project_id: str,
        user_id: int,
        chat_id: int,
        message_id: int,
        status_message_id: int,
        prompt: str,
    ) -> int:
        """Create a new request and launch the Claude process."""
        if self._shutting_down:
            raise RuntimeError("Pandemonium bot is shutting down, not accepting new requests")

        if self._active and self._active.state in (
            SessionState.RUNNING,
            SessionState.AWAITING_INPUT,
        ):
            raise RuntimeError("A request is already in progress")

        req_number = self._storage.next_request_number(project_id)

        request_id = await db.create_request(
            self._db,
            project_id=project_id,
            user_id=user_id,
            request_number=req_number,
            message_id=message_id,
            status_msg_id=status_message_id,
            chat_id=chat_id,
        )

        await self._storage.save_request(project_id, req_number, prompt)

        process = ClaudeProcess()
        session = ActiveSession(
            request_id=request_id,
            request_number=req_number,
            project_id=project_id,
            chat_id=chat_id,
            user_message_id=message_id,
            status_message_id=status_message_id,
            state=SessionState.RUNNING,
            claude_process=process,
            active_project_id=self._active_project_id,
            active_persona=self._active_persona,
        )
        self._active = session

        await db.update_request_status(self._db, request_id, "running")

        session.process_task = asyncio.create_task(
            self._run_session(session, prompt),
        )
        return req_number

    async def cancel_request(self, request_id: int) -> None:
        """Cancel the active request."""
        session = self._active
        if not session or session.request_id != request_id:
            return
        if session.state not in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
            return

        session.state = SessionState.CANCELLED
        if session.pending_response and not session.pending_response.done():
            session.pending_response.cancel()
        await session.claude_process.cancel()
        await db.update_request_status(self._db, request_id, "cancelled")
        logger.info("Request %s cancelled", request_id)

    async def handle_permission_response(
        self, request_id: int, allowed: bool,
    ) -> None:
        """User responded to a permission request (Allow/Deny)."""
        session = self._active
        if not session or session.request_id != request_id:
            return
        if session.state != SessionState.AWAITING_INPUT:
            return

        response_text = "Allowed" if allowed else "Denied"
        await self._storage.save_interaction(
            session.project_id, session.request_number,
            session.sub_counter, response_text, is_response=True,
        )
        await db.create_interaction(
            self._db, request_id, session.sub_counter,
            "permission", "from_user", response_text,
        )

        await session.claude_process.send_permission(allowed)

        session.state = SessionState.RUNNING
        await db.update_request_status(self._db, request_id, "running")

        if session.pending_response and not session.pending_response.done():
            session.pending_response.set_result(allowed)

    async def handle_user_reply(self, request_id: int, text: str) -> None:
        """User replied to a clarifying question."""
        session = self._active
        if not session or session.request_id != request_id:
            return
        if session.state != SessionState.AWAITING_INPUT:
            return

        await self._storage.save_interaction(
            session.project_id, session.request_number,
            session.sub_counter, text, is_response=True,
        )
        await db.create_interaction(
            self._db, request_id, session.sub_counter,
            "question", "from_user", text,
        )

        await session.claude_process.send_input(text)

        session.state = SessionState.RUNNING
        await db.update_request_status(self._db, request_id, "running")

        if session.pending_response and not session.pending_response.done():
            session.pending_response.set_result(text)

    async def shutdown(self) -> None:
        """Graceful shutdown — cancel active session, notify user."""
        self._shutting_down = True
        session = self._active
        if session and session.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
            logger.info("Shutting down: cancelling request #%s", session.request_number)
            await telegram_retry(lambda: self._bot.send_message(
                chat_id=session.chat_id,
                text=f"Pandemonium bot is restarting. Request #{session.request_number} interrupted.",
                reply_to_message_id=session.user_message_id,
            ))
            session.state = SessionState.ERROR
            if session.pending_response and not session.pending_response.done():
                session.pending_response.cancel()
            await session.claude_process.cancel()
            await db.update_request_status(
                self._db, session.request_id, "error",
                error_text="Pandemonium bot shutdown",
            )
            await self._storage.save_error(
                session.project_id, session.request_number, "Pandemonium bot shutdown",
            )

    # ── Private ───────────────────────────────────────────────────────────

    def _build_persona_prompt(self) -> str | None:
        """Read active persona and its soul from the default project.

        Only called when active project is the default (pandemonium-bot).
        Returns combined PERSONA.md + SOUL.md text, or None.
        """
        if not self._active_persona:
            return None

        bot_root = Path(__file__).resolve().parents[4]
        persona_file = (
            bot_root / ".agent" / "personas"
            / self._active_persona / "PERSONA.md"
        )
        if not persona_file.is_file():
            logger.warning("Persona file not found: %s", persona_file)
            return None

        parts: list[str] = [
            f"# Active Persona: {self._active_persona}\n",
            persona_file.read_text(encoding="utf-8"),
        ]

        # Check if persona has a soul (from YAML frontmatter)
        soul_name: str | None = None
        try:
            import yaml
            content = persona_file.read_text(encoding="utf-8")
            if content.startswith("---"):
                end = content.index("---", 3)
                frontmatter = yaml.safe_load(content[3:end])
                soul_name = (frontmatter or {}).get("soul")
        except Exception:
            pass

        if soul_name:
            soul_file = bot_root / ".agent" / "souls" / soul_name / "SOUL.md"
            if soul_file.is_file():
                parts.append(f"\n# Soul: {soul_name}\n")
                parts.append(soul_file.read_text(encoding="utf-8"))
            else:
                logger.warning("Soul file not found: %s", soul_file)

        return "\n".join(parts)

    async def _run_session(self, session: ActiveSession, prompt: str) -> None:
        """Main session loop — runs as a background task."""
        active_project = (
            self._config.get_project(self._active_project_id)
            or self._config.default_project
        )
        is_default_project = (active_project.id == self._config.default_project.id)
        timeout = self._config.timeouts.request_max_seconds
        token_limit = self._config.token_budget.per_request_limit
        tokens_accumulated = 0

        try:
            bot_root = Path(__file__).resolve().parents[4]
            send_file_script = str(
                bot_root / ".pandemonium" / "tools" / "send_file.sh",
            )

            extra_env = {
                "PANDEMONIUM_BOT_TOKEN": self._config.telegram.bot_token,
                "PANDEMONIUM_CHAT_ID": str(session.chat_id),
                "PANDEMONIUM_SEND_FILE": send_file_script,
            }

            # Persona prompt only for the default project (pandemonium-bot).
            # External projects use their own CLAUDE.md — we don't inject anything.
            persona_prompt = self._build_persona_prompt() if is_default_project else None

            # Snapshot resume ID before starting (prevents race with init event).
            resume_id = self._next_resume_id

            # Run Claude Code from the active project's directory so it
            # picks up that project's CLAUDE.md as the system prompt.
            await session.claude_process.start(
                prompt, active_project.path,
                resume_session_id=resume_id,
                extra_env=extra_env,
                append_system_prompt=persona_prompt,
            )
            session.typing_task = asyncio.create_task(
                self._typing_loop(session.chat_id),
            )

            buffer = StreamBuffer(
                flush_callback=lambda text: self._send_chunk(session, text),
            )

            async def _event_loop() -> None:
                nonlocal tokens_accumulated
                async for event in session.claude_process.stream_events():
                    if session.state == SessionState.CANCELLED:
                        break

                    match event:
                        case SystemEvent(subtype="init", session_id=sid) if sid:
                            self._next_resume_id = sid
                            logger.info("Claude session ID: %s", sid)

                        case AssistantEvent(text=text, usage=usage):
                            await buffer.append(text)
                            await self._storage.append_stream_log(
                                session.project_id, session.request_number, text,
                            )
                            # Track token usage for limit enforcement
                            if usage:
                                tokens_accumulated = (
                                    usage.input_tokens + usage.output_tokens
                                )
                                if token_limit > 0 and tokens_accumulated > token_limit:
                                    await buffer.close()
                                    await self._handle_token_limit(
                                        session, token_limit, tokens_accumulated,
                                    )
                                    return

                        case ToolUseEvent(tool=tool):
                            logger.info("Tool use: %s", tool)

                        case PermissionRequestEvent(tool=tool, description=desc):
                            await buffer.flush()
                            await self._handle_permission_request(session, tool, desc)

                        case InputRequestEvent(question=question):
                            await buffer.flush()
                            await self._handle_input_request(session, question)

                        case ResultEvent(text=text, usage=usage, is_error=is_err):
                            await buffer.close()
                            if is_err:
                                await self._handle_error(session, text)
                            else:
                                await self._handle_result(session, text, usage)

            # Apply request timeout
            try:
                await asyncio.wait_for(_event_loop(), timeout=timeout)
            except TimeoutError:
                if session.state in (SessionState.RUNNING, SessionState.AWAITING_INPUT):
                    await buffer.close()
                    await session.claude_process.cancel()
                    await self._handle_error(
                        session,
                        f"Request timed out after {timeout // 60} minutes.",
                    )
                    return

            # Process exited — check for non-zero exit code
            if session.state == SessionState.RUNNING:
                exit_code = await session.claude_process.wait()
                if exit_code != 0:
                    stderr = session.claude_process.stderr_output
                    error_msg = stderr or f"Claude Code exited with code {exit_code}"
                    await self._handle_error(session, error_msg)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Session error")
            if session.state not in (
                SessionState.COMPLETED,
                SessionState.CANCELLED,
                SessionState.ERROR,
            ):
                await self._handle_error(session, str(exc))
        finally:
            await self._finalize(session)

    async def _handle_token_limit(
        self, session: ActiveSession, limit: int, used: int,
    ) -> None:
        """Cancel session when token limit is exceeded."""
        await session.claude_process.cancel()
        error_msg = (
            f"Token limit exceeded ({used:,} / {limit:,}). Request stopped."
        )
        await self._handle_error(session, error_msg)

    async def _handle_permission_request(
        self, session: ActiveSession, tool: str, description: str,
    ) -> None:
        """Send permission request to user and wait for response."""
        session.sub_counter += 1
        session.state = SessionState.AWAITING_INPUT
        await db.update_request_status(self._db, session.request_id, "awaiting_input")

        content = f"Permission request: **{tool}**\n{description}"
        html_content = md_to_telegram_html(content)

        await self._storage.save_interaction(
            session.project_id, session.request_number,
            session.sub_counter, content, is_response=False,
        )
        msg = await self._bot.send_message(
            chat_id=session.chat_id,
            text=html_content,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=session.user_message_id,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Allow",
                    callback_data=f"perm:{session.request_id}:allow",
                ),
                InlineKeyboardButton(
                    text="Deny",
                    callback_data=f"perm:{session.request_id}:deny",
                ),
            ]]),
        )
        await db.create_interaction(
            self._db, session.request_id, session.sub_counter,
            "permission", "from_claude", content, msg.message_id,
        )

        loop = asyncio.get_running_loop()
        session.pending_response = loop.create_future()
        try:
            await session.pending_response
        except asyncio.CancelledError:
            pass
        finally:
            session.pending_response = None

    async def _handle_input_request(
        self, session: ActiveSession, question: str,
    ) -> None:
        """Send clarifying question to user and wait for reply."""
        session.sub_counter += 1
        session.state = SessionState.AWAITING_INPUT
        await db.update_request_status(self._db, session.request_id, "awaiting_input")

        await self._storage.save_interaction(
            session.project_id, session.request_number,
            session.sub_counter, question, is_response=False,
        )
        msg = await self._bot.send_message(
            chat_id=session.chat_id,
            text=question,
            reply_to_message_id=session.user_message_id,
        )
        await db.create_interaction(
            self._db, session.request_id, session.sub_counter,
            "question", "from_claude", question, msg.message_id,
        )

        loop = asyncio.get_running_loop()
        session.pending_response = loop.create_future()
        try:
            await session.pending_response
        except asyncio.CancelledError:
            pass
        finally:
            session.pending_response = None

    async def _send_chunk(self, session: ActiveSession, text: str) -> None:
        """Send a text chunk as a Telegram message with HTML formatting."""
        html = truncate_html(md_to_telegram_html(text))
        try:
            await telegram_retry(lambda: self._bot.send_message(
                chat_id=session.chat_id,
                text=html,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=session.user_message_id,
            ))
        except Exception:
            # Fallback to plain text if HTML parsing fails
            truncated = text[:4000] if len(text) > 4000 else text
            await telegram_retry(lambda: self._bot.send_message(
                chat_id=session.chat_id,
                text=truncated,
                reply_to_message_id=session.user_message_id,
            ))

    async def _handle_result(self, session: ActiveSession, text: str, usage) -> None:
        """Process a successful result event."""
        session.state = SessionState.COMPLETED

        await self._storage.save_report(
            session.project_id, session.request_number, text,
        )
        await db.update_request_status(
            self._db,
            session.request_id,
            "completed",
            tokens_input=usage.input_tokens,
            tokens_output=usage.output_tokens,
        )

        report_bytes = text.encode("utf-8")
        doc = BufferedInputFile(
            file=report_bytes,
            filename=f"report_{session.request_number}.md",
        )
        await telegram_retry(lambda: self._bot.send_document(
            chat_id=session.chat_id,
            document=doc,
            reply_to_message_id=session.user_message_id,
        ))

    async def _handle_error(self, session: ActiveSession, error_text: str) -> None:
        """Process an error."""
        session.state = SessionState.ERROR
        await self._storage.save_error(
            session.project_id, session.request_number, error_text,
        )
        await db.update_request_status(
            self._db, session.request_id, "error", error_text=error_text,
        )

        display = error_text[:4000] if len(error_text) > 4000 else error_text
        await telegram_retry(lambda: self._bot.send_message(
            chat_id=session.chat_id,
            text=f"Error: {display}",
            reply_to_message_id=session.user_message_id,
        ))

    async def _finalize(self, session: ActiveSession) -> None:
        """Clean up after a session ends."""
        if session.typing_task and not session.typing_task.done():
            session.typing_task.cancel()
            try:
                await session.typing_task
            except asyncio.CancelledError:
                pass

        tokens_row = await db.get_token_totals(self._db, session.project_id)
        meta = {
            "request_number": session.request_number,
            "status": session.state.value,
            "tokens_used": {
                "input": tokens_row["input"],
                "output": tokens_row["output"],
                "total": tokens_row["total"],
            },
        }
        await self._storage.save_meta(
            session.project_id, session.request_number, meta,
        )

        from pandemonium.tgbot.bot.formatters import format_status_message
        try:
            await self._bot.edit_message_text(
                chat_id=session.chat_id,
                message_id=session.status_message_id,
                text=format_status_message(session.request_number, session.state),
            )
        except Exception:
            logger.debug("Could not update status message", exc_info=True)

        if session.state not in (SessionState.COMPLETED, SessionState.CANCELLED, SessionState.ERROR):
            session.state = SessionState.COMPLETED

        logger.info(
            "Session finalized: request #%s, status=%s",
            session.request_number, session.state.value,
        )

    async def _typing_loop(self, chat_id: int) -> None:
        """Send typing action every 5 seconds."""
        try:
            while True:
                await self._bot.send_chat_action(
                    chat_id=chat_id,
                    action=ChatAction.TYPING,
                )
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
