"""Parsing of Claude Code stream-json events.

Claude Code with `--output-format stream-json` emits JSON objects one per line.

Permission requests and input requests are signalled via specific subtype fields:
- Permission: {"type": "system", "subtype": "permission_request",
    "tool": "Bash", "description": "Run command: ls -la"}
- Input request: {"type": "system", "subtype": "input_request",
    "question": "Which file should I modify?"}

If Claude Code uses a different mechanism (e.g. tool_use blocks with special
names, or stderr prompts), the parser should be updated accordingly.
"""

import json
import logging

from pandemonium.tgbot.claude.types import (
    AssistantEvent,
    ClaudeEvent,
    InputRequestEvent,
    PermissionRequestEvent,
    ResultEvent,
    SystemEvent,
    TokenUsage,
    ToolResultEvent,
    ToolUseEvent,
)

logger = logging.getLogger(__name__)


def _parse_usage(raw: dict | None) -> TokenUsage | None:
    if not raw:
        return None
    return TokenUsage(
        input_tokens=raw.get("input_tokens", 0),
        output_tokens=raw.get("output_tokens", 0),
    )


def _extract_assistant_text(message: dict) -> str:
    """Extract concatenated text from assistant message content blocks."""
    content = message.get("content", [])
    parts: list[str] = []
    for block in content:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def _extract_tool_use(message: dict) -> ToolUseEvent | None:
    """Extract the first tool_use block from assistant message."""
    content = message.get("content", [])
    for block in content:
        if block.get("type") == "tool_use":
            return ToolUseEvent(
                tool=block.get("name", "unknown"),
                input=block.get("input", {}),
            )
    return None


def parse_event(line: str) -> ClaudeEvent | None:
    """Parse a single JSON line from Claude Code stdout.

    Returns None for unknown or unparseable events.
    """
    line = line.strip()
    if not line:
        return None

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        logger.warning("Non-JSON line from Claude Code: %.200s", line)
        return None

    if not isinstance(data, dict):
        return None

    event_type = data.get("type")

    match event_type:
        case "system":
            subtype = data.get("subtype", "")

            match subtype:
                case "permission_request":
                    return PermissionRequestEvent(
                        tool=data.get("tool", "unknown"),
                        description=data.get("description", ""),
                    )
                case "input_request":
                    return InputRequestEvent(
                        question=data.get("question", ""),
                    )
                case _:
                    return SystemEvent(
                        subtype=subtype,
                        session_id=data.get("session_id"),
                    )

        case "assistant":
            message = data.get("message", {})
            content = message.get("content", [])

            # Check if this is a tool_use message
            for block in content:
                if block.get("type") == "tool_use":
                    return _extract_tool_use(message)

            # Otherwise it's a text message
            text = _extract_assistant_text(message)
            if text:
                return AssistantEvent(
                    text=text,
                    usage=_parse_usage(data.get("usage")),
                )
            return None

        case "result":
            usage = _parse_usage(data.get("usage"))
            if not usage:
                usage = TokenUsage(input_tokens=0, output_tokens=0)
            return ResultEvent(
                text=data.get("result", ""),
                usage=usage,
                is_error=data.get("is_error", False),
            )

        case _:
            logger.debug("Unknown Claude event type: %s", event_type)
            return None
