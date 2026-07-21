"""Claude Code stream-json event types."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class SystemEvent:
    subtype: str
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantEvent:
    text: str
    usage: TokenUsage | None = None


@dataclass(frozen=True, slots=True)
class ToolUseEvent:
    tool: str
    input: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResultEvent:
    tool: str
    output: str


@dataclass(frozen=True, slots=True)
class ResultEvent:
    text: str
    usage: TokenUsage
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class PermissionRequestEvent:
    """Claude Code requests permission to use a tool."""
    tool: str
    description: str


@dataclass(frozen=True, slots=True)
class InputRequestEvent:
    """Claude Code asks the user a clarifying question."""
    question: str


@dataclass(frozen=True, slots=True)
class AskUserQuestionEvent:
    """Claude used the AskUserQuestion tool — question(s) with answer options.

    Each question is a dict: {"question", "header", "options": [{"label",
    "description"}], "multiSelect"}.
    """
    questions: list[dict] = field(default_factory=list)


type ClaudeEvent = (
    SystemEvent
    | AssistantEvent
    | ToolUseEvent
    | ToolResultEvent
    | ResultEvent
    | PermissionRequestEvent
    | InputRequestEvent
    | AskUserQuestionEvent
)
