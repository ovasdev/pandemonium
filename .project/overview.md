# Pandemonium Telegram bot

## Назначение

Telegram-бот на Python, выступающий мостом между пользователем и Claude Code CLI.
Пользователь пишет запрос в Telegram → бот запускает `claude` в контексте проекта →
стримит промежуточные результаты → возвращает итоговый отчёт.

## Стек

- Python 3.12+ (asyncio, match/case, `X | Y` unions)
- aiogram 3.x — Telegram Bot API
- aiosqlite — async SQLite
- pydantic 2.x — валидация конфига
- PyYAML — парсинг конфига
- uv — менеджер пакетов

## Статус

Все 6 спринтов завершены. 89 тестов проходят.

| Спринт | Фокус | Коммит |
|--------|-------|--------|
| 1 | Config, DB, bot skeleton | `4d6a71c` |
| 2 | ClaudeProcess, event parsing | `2dcb468` |
| 3 | ProtocolStorage, DB CRUD | `060b31c` |
| 4 | SessionManager, main flow | `eddf9e1` |
| 5 | Permission/input, Future wait | `0fe3d49` |
| 6 | Commands, tokens, polish | `cf6b39c` |

## Структура каталогов

```
├── CLAUDE.md                # Инструкции для агента
├── pyproject.toml           # Зависимости, pytest config
├── config.example.yaml      # Пример конфига (рабочий: ~/.pandemonium/config.yaml)
├── start.sh / stop.sh       # Запуск/остановка бота
├── .project/                # ← ЭТИ ФАЙЛЫ (контекст для агента)
├── .agent/skills/           # Справочные материалы по разработке
├── docs/                    # Требования, архитектура, спринты
├── src/pandemonium/tgbot/   # Исходный код
│   ├── __init__.py          # version = "0.1.0"
│   ├── __main__.py          # Entry: `uv run python -m pandemonium.tgbot`
│   ├── main.py              # App startup, shutdown, recovery
│   ├── config.py            # Pydantic config models
│   ├── db.py                # SQLite schema + CRUD
│   ├── bot/                 # Telegram layer
│   │   ├── handlers.py      # /start, /status, /history, /tokens, text
│   │   ├── callbacks.py     # Cancel, Allow/Deny buttons
│   │   ├── middleware.py    # AuthMiddleware (whitelist)
│   │   ├── retry.py         # Exponential backoff for TG API
│   │   ├── formatters.py    # Message formatting
│   │   └── markup.py        # Markdown → Telegram HTML
│   ├── claude/              # Claude Code subprocess
│   │   ├── process.py       # ClaudeProcess class
│   │   ├── types.py         # Event dataclasses
│   │   └── events.py        # JSON line parser
│   ├── session/             # Session orchestration
│   │   ├── manager.py       # SessionManager (координатор)
│   │   ├── state.py         # ActiveSession, SessionState enum
│   │   └── buffer.py        # StreamBuffer (debounced flush)
│   └── storage/
│       └── protocol.py      # Filesystem protocol logging
└── tests/                   # pytest + pytest-asyncio (89 tests)
```

## Entry Point

```
uv run python -m pandemonium.tgbot  →  src/pandemonium/tgbot/__main__.py  →  pandemonium.tgbot.main.cli()  →  asyncio.run(main())
```

## Конфиг (runtime)

`~/.pandemonium/config.yaml` — telegram token, allowed users, projects, storage path, token budget, timeouts.
