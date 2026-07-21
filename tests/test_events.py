"""Tests for Claude Code event parsing."""

import json

from pandemonium.tgbot.claude.events import parse_event
from pandemonium.tgbot.claude.types import (
    AskUserQuestionEvent,
    AssistantEvent,
    InputRequestEvent,
    PermissionRequestEvent,
    ResultEvent,
    SystemEvent,
    TokenUsage,
    ToolUseEvent,
)


def test_parse_system_event():
    line = json.dumps({
        "type": "system",
        "subtype": "init",
        "session_id": "abc-123",
    })
    event = parse_event(line)
    assert isinstance(event, SystemEvent)
    assert event.subtype == "init"
    assert event.session_id == "abc-123"


def test_parse_assistant_text_event():
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello world"}],
        },
        "usage": {"input_tokens": 100, "output_tokens": 50},
    })
    event = parse_event(line)
    assert isinstance(event, AssistantEvent)
    assert event.text == "Hello world"
    assert event.usage == TokenUsage(input_tokens=100, output_tokens=50)


def test_parse_assistant_text_no_usage():
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hi"}],
        },
    })
    event = parse_event(line)
    assert isinstance(event, AssistantEvent)
    assert event.text == "Hi"
    assert event.usage is None


def test_parse_assistant_multi_text_blocks():
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Part 1"},
                {"type": "text", "text": " Part 2"},
            ],
        },
    })
    event = parse_event(line)
    assert isinstance(event, AssistantEvent)
    assert event.text == "Part 1 Part 2"


def test_parse_tool_use_event():
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": "tool-1",
                "name": "Write",
                "input": {"path": "/tmp/test.py", "content": "print('hi')"},
            }],
        },
    })
    event = parse_event(line)
    assert isinstance(event, ToolUseEvent)
    assert event.tool == "Write"
    assert event.input["path"] == "/tmp/test.py"


def test_parse_ask_user_question_event():
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": "tool-2",
                "name": "AskUserQuestion",
                "input": {
                    "questions": [{
                        "question": "Which library should we use?",
                        "header": "Library",
                        "multiSelect": False,
                        "options": [
                            {"label": "aiogram", "description": "Async Telegram framework"},
                            {"label": "pyTelegramBotAPI", "description": "Sync alternative"},
                        ],
                    }],
                },
            }],
        },
    })
    event = parse_event(line)
    assert isinstance(event, AskUserQuestionEvent)
    assert len(event.questions) == 1
    q = event.questions[0]
    assert q["question"] == "Which library should we use?"
    assert [o["label"] for o in q["options"]] == ["aiogram", "pyTelegramBotAPI"]


def test_parse_ask_user_question_empty_input():
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": "tool-3",
                "name": "AskUserQuestion",
                "input": {},
            }],
        },
    })
    event = parse_event(line)
    assert isinstance(event, AskUserQuestionEvent)
    assert event.questions == []


def test_parse_result_event():
    line = json.dumps({
        "type": "result",
        "result": "Task completed successfully.",
        "usage": {"input_tokens": 5000, "output_tokens": 1200},
        "is_error": False,
    })
    event = parse_event(line)
    assert isinstance(event, ResultEvent)
    assert event.text == "Task completed successfully."
    assert event.usage.input_tokens == 5000
    assert event.usage.output_tokens == 1200
    assert event.is_error is False


def test_parse_result_error():
    line = json.dumps({
        "type": "result",
        "result": "Something went wrong",
        "usage": {"input_tokens": 100, "output_tokens": 10},
        "is_error": True,
    })
    event = parse_event(line)
    assert isinstance(event, ResultEvent)
    assert event.is_error is True


def test_parse_unknown_type():
    line = json.dumps({"type": "unknown_custom_type", "data": "foo"})
    assert parse_event(line) is None


def test_parse_empty_line():
    assert parse_event("") is None
    assert parse_event("   ") is None


def test_parse_invalid_json():
    assert parse_event("not json at all") is None


def test_parse_non_dict_json():
    assert parse_event("[1, 2, 3]") is None


def test_parse_assistant_empty_content():
    line = json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "content": []},
    })
    assert parse_event(line) is None


def test_parse_result_no_usage():
    """Result without usage should still parse with zero tokens."""
    line = json.dumps({
        "type": "result",
        "result": "done",
    })
    event = parse_event(line)
    assert isinstance(event, ResultEvent)
    assert event.usage == TokenUsage(input_tokens=0, output_tokens=0)


def test_parse_permission_request():
    line = json.dumps({
        "type": "system",
        "subtype": "permission_request",
        "tool": "Bash",
        "description": "Run command: rm -rf /tmp/test",
    })
    event = parse_event(line)
    assert isinstance(event, PermissionRequestEvent)
    assert event.tool == "Bash"
    assert "rm -rf" in event.description


def test_parse_input_request():
    line = json.dumps({
        "type": "system",
        "subtype": "input_request",
        "question": "Which file should I modify?",
    })
    event = parse_event(line)
    assert isinstance(event, InputRequestEvent)
    assert event.question == "Which file should I modify?"


def test_parse_system_init_still_works():
    """Regular system events should still parse as SystemEvent."""
    line = json.dumps({
        "type": "system",
        "subtype": "init",
        "session_id": "s123",
    })
    event = parse_event(line)
    assert isinstance(event, SystemEvent)
    assert event.subtype == "init"
