# Архитектура Pandemonium bot

## Компоненты и связи

```
Telegram User
    ↕ (aiogram 3.x)
Bot Layer (handlers.py, callbacks.py, middleware.py)
    ↕ (DI через dp["session_manager"])
SessionManager (manager.py)
    ↕                          ↕
ClaudeProcess (process.py)   ProtocolStorage (protocol.py)
    ↕                          ↕
claude CLI subprocess        Filesystem (~/.pandemonium/sessions/)
                               ↕
                           SQLite (pandemonium.db)
```

## Принцип: ClaudeProcess не знает о Telegram

`ClaudeProcess` — чистая обёртка над subprocess. Не импортирует aiogram.
`SessionManager` — координатор, связывает Telegram-события с Claude-событиями.

## Dependency Injection

Через aiogram dispatcher:
```python
dp["config"] = AppConfig
dp["db"] = aiosqlite.Connection
dp["session_manager"] = SessionManager
```

Handlers получают зависимости как типизированные параметры.

## Жизненный цикл запроса

1. User sends text → `handle_text_message()` в handlers.py
2. Handler создаёт status message с кнопкой Cancel
3. `session_manager.create_request()` → creates DB record, spawns `_run_session()` task
4. `_run_session()` запускает `ClaudeProcess.start()` → claude subprocess
5. Event loop: `stream_events()` → match/case по типу события:
   - `AssistantEvent` → accumulate in StreamBuffer → flush to Telegram
   - `PermissionRequestEvent` → send Allow/Deny buttons, wait for Future
   - `InputRequestEvent` → send question, wait for reply, resolve Future
   - `ResultEvent` → save report, send as document
6. `_finalize()` → cancel typing, save meta.json, update status message

## Единственная активная сессия

Одновременно обрабатывается один запрос. Повторный запрос → ошибка.
`_active: ActiveSession | None` в SessionManager.

## Session ID Continuity

`--resume {session_id}` сохраняет контекст разговора между запросами.
Кешируется в `SessionManager._claude_session_id`.
Сбрасывается через `/clear`.

## Двойное хранение

- **SQLite** (`pandemonium.db`): операционные данные — статусы, токены, history.
- **Filesystem** (`~/.pandemonium/sessions/{project_id}/request_{N}/`): подробные логи — request.md, stream_log.md, report.md, meta.json, interactions.

## StreamBuffer

Накапливает текст от Claude, отправляет пачкой в Telegram:
- Таймер 2.5 сек (debounce)
- Порог 3500 символов (принудительный flush)
- Предотвращает rate limit от Telegram API

## Graceful Shutdown

1. SIGTERM/SIGINT → `shutdown_event.set()`
2. `session_manager.shutdown()` → уведомляет пользователя, отменяет процесс
3. Recovery при запуске: `_recover_interrupted_requests()` помечает незавершённые как error

## Auth

`AuthMiddleware(BaseMiddleware)` — проверяет telegram_id по whitelist из конфига.
Блокирует и Message, и CallbackQuery.

## Retry

`telegram_retry(fn, max_retries=3)` — exponential backoff для TelegramNetworkError/TelegramRetryAfter.
