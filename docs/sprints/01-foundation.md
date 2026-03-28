# Спринт 1 — Фундамент проекта

## Цель

Настроить проект, реализовать загрузку конфига, инициализацию БД и минимальный Telegram-бот, который запускается, проверяет авторизацию и отвечает на `/start`.

## Задачи

### 1.1 Структура проекта

Создать структуру папок согласно `architecture.md` п. 2:

```
pandemonium-bot/
├── pyproject.toml
├── config.example.yaml
├── src/
│   └── pandemonium/tgbot/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── bot/
│       │   ├── __init__.py
│       │   ├── handlers.py
│       │   ├── middleware.py
│       │   └── formatters.py
│       ├── claude/
│       │   └── __init__.py
│       ├── session/
│       │   └── __init__.py
│       └── storage/
│           └── __init__.py
└── tests/
```

`pyproject.toml` — зависимости: aiogram, aiosqlite, pyyaml, pydantic.
Менеджер пакетов: uv.

### 1.2 Config (`config.py`)

- Pydantic-модели: `AppConfig`, `TelegramConfig`, `UserConfig`, `ProjectConfig`, `StorageConfig`, `TokenBudgetConfig` — согласно `architecture.md` п. 3.1.
- Функция `load_config(path: Path) -> AppConfig` — читает YAML, валидирует.
- Путь к конфигу — из аргумента CLI или переменной окружения `PANDEMONIUM_CONFIG` или дефолт `~/.pandemonium/config.yaml`.

### 1.3 Database (`db.py`)

- Функция `init_db(path: Path) -> aiosqlite.Connection`.
- Создание таблиц `requests` и `interactions` — схема из `architecture.md` п. 3.2.
- БД файл: `{storage.base_path}/pandemonium.db`.

### 1.4 Telegram-бот (минимальный)

- `main.py` — точка входа: загрузка конфига, инициализация БД, запуск бота (long polling).
- `bot/middleware.py` — middleware авторизации: проверка `user_id` против `allowed_users`. Неавторизованным — ответ "Access denied".
- `bot/handlers.py` — обработчик `/start`: приветствие с именем пользователя и названием проекта.

### 1.5 config.example.yaml

Пример конфига с комментариями.

## Критерий готовности

- `uv run python -m pandemonium.tgbot` запускает бота.
- Бот отвечает на `/start` авторизованному пользователю.
- Бот отклоняет неавторизованных.
- БД файл создаётся с правильной схемой.
- Невалидный конфиг → понятная ошибка при старте.
