---
name: testing-tca
description: "Runs and writes tests for the Pandemonium bot project using pytest and pytest-asyncio. Triggers when working on Pandemonium bot code that needs testing, when the user asks to run tests, or before committing changes. Also triggers when debugging test failures or adding test coverage."
compatibility: "Requires Python 3.12+, uv, pytest, pytest-asyncio"
---

# Testing Pandemonium bot

Run and write tests for the Pandemonium Telegram bot project.

## Running Tests

```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/test_config.py

# Verbose output
uv run pytest -v

# Single test
uv run pytest tests/test_config.py::test_load_valid_config
```

## App Startup Check

```bash
uv run python -m pandemonium.tgbot --config config.example.yaml
# Ctrl+C to stop — verifies the app starts without errors
```

## Type Checking

```bash
uv run mypy src/pandemonium/tgbot/
```

## What to Test

| Module | Focus |
|---|---|
| `config.py` | Valid config loads; invalid config raises with clear message |
| `db.py` | CRUD operations, status correctness, token counting |
| `storage/protocol.py` | Folder creation, file writes, numbering increment |
| `claude/events.py` | JSON event parsing for all types, resilience to invalid JSON |
| `session/buffer.py` | Debounce, flush on size, flush on close |

## Mocking Rules

- **Claude Code process** → `unittest.mock.AsyncMock`
- **Telegram API** → mock `Bot` object, never call real API
- **Filesystem** → `tmp_path` fixture
- **SQLite** → in-memory (`:memory:`)
