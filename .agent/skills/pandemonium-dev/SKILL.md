---
name: pandemonium-dev
description: "Development rules and conventions for the Pandemonium Telegram bot project. Triggers when working on pandemonium-bot code: writing Python, running tests, implementing sprints, reviewing architecture. Also triggers on: 'реализуй спринт', 'напиши код', 'запусти тесты', 'исправь баг'. Does NOT apply when working on other active projects — each project has its own conventions."
---

# Pandemonium Dev

Rules and conventions for developing the Pandemonium Telegram bot.

---

## Stack

- **Python 3.12+** with asyncio
- **aiogram 3.x** — Telegram Bot API
- **aiosqlite** — async SQLite
- **pydantic 2.x** — config validation
- **PyYAML** — config parsing
- **uv** — package manager

## Code

- Python 3.12+ syntax: `X | Y` for union, `match/case`, `type` aliases.
- Type annotations mandatory for all public functions.
- All I/O is async (`async/await`).
- Logging via `logging`, never `print()`.
- Custom exceptions inherit from `PandemoniumError`.
- Never suppress `CancelledError` in async code.

## Architecture

- Follow `docs/architecture.md`. Don't change it without explicit request.
- Components wired via dependency injection (aiogram `dp[...]`).
- `ClaudeProcess` knows nothing about Telegram. `SessionManager` coordinates between them.

## Project Context

Before starting work, read `.project/` files for full project description:

- `.project/overview.md` — purpose, stack, status, directory structure, entry point
- `.project/architecture.md` — components, lifecycle, DI, storage
- `.project/api-reference.md` — all classes, methods, signatures
- `.project/database.md` — SQLite schema (requests, interactions tables), statuses
- `.project/gotchas.md` — critical gotchas (env vars, --verbose, pydantic, aiogram exceptions)
- `.project/testing.md` — test structure, rules

## Documentation

All project docs in `docs/`:

- `requirements.md` — functional requirements (read before starting work)
- `architecture.md` — technical architecture, components, data flows
- `future.md` — deferred features (don't implement, but consider in architecture)
- `sprints/` — sprint tasks and acceptance criteria

Read `requirements.md` and `architecture.md` before executing any sprint.

## Sprints

- One sprint at a time.
- Follow task order in the sprint file.
- Before committing — verify all acceptance criteria.
- Commit message: `sprint N: brief description`.

## Tests

- Framework: `pytest` + `pytest-asyncio`.
- Mock external dependencies (Telegram API, Claude Code process).
- File tests — via `tmp_path`.
- SQLite tests — via in-memory (`:memory:`).
- Run: `uv run pytest`.

## Don'ts

- Don't implement features from `future.md` — only consider them architecturally.
- Don't add dependencies not listed in architecture without explicit request.
- Don't modify docs in `docs/`.
- Don't use `--dangerously-skip-permissions` when running Claude Code by default.
