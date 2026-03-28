# Тестирование

## Запуск

```bash
uv run pytest           # все тесты
uv run pytest -v        # verbose
uv run pytest tests/test_session.py  # конкретный файл
```

## Настройки

- Фреймворк: pytest + pytest-asyncio
- `asyncio_mode = "auto"` в pyproject.toml — все async тесты запускаются автоматически
- testpaths: `["tests"]`

## Тестовые файлы (89 тестов)

| Файл | Тестов | Что тестирует |
|------|--------|---------------|
| test_config.py | 6 | Загрузка YAML, валидация, ошибки |
| test_db.py | 18 | Схема, CRUD, constraints |
| test_process.py | 5 | ClaudeProcess lifecycle, cancel, stderr |
| test_events.py | 17 | Парсинг JSON-событий из Claude |
| test_buffer.py | 8 | StreamBuffer debounce, flush |
| test_storage.py | 9 | Filesystem protocol logging |
| test_session.py | 13 | SessionManager orchestration |
| test_retry.py | 6 | Telegram API retry logic |
| test_bot.py | 7 | Handlers, middleware |
| test_commands.py | 3 | Форматирование /status, /history, /tokens |

## Правила

- Мокать внешние зависимости (Telegram API, Claude subprocess)
- Файловые тесты — через `tmp_path` fixture
- SQLite тесты — через in-memory (`:memory:`)
- Не подавлять `CancelledError`
- aiogram exceptions требуют mock method: `TelegramNetworkError(MagicMock(), "msg")`
