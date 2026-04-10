"""Session state machine and active session data."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum

from pandemonium.tgbot.claude.process import ClaudeProcess


class SessionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class ActiveSession:
    request_id: int
    request_number: int
    project_id: str
    chat_id: int
    user_message_id: int
    status_message_id: int
    state: SessionState
    claude_process: ClaudeProcess
    typing_task: asyncio.Task | None = None
    process_task: asyncio.Task | None = None
    active_project_id: str | None = None
    active_persona: str | None = None
    sub_counter: int = field(default=0)
    pending_response: asyncio.Future | None = field(default=None, repr=False)
    cancel_message_ids: list[int] = field(default_factory=list)
