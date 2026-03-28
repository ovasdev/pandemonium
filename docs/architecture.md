# Pandemonium Telegram bot — Архитектура

## 1. Выбор стека

| Компонент        | Решение                   | Обоснование                                                    |
|------------------|---------------------------|----------------------------------------------------------------|
| Язык             | **Python 3.12+**          | asyncio из коробки, отличные библиотеки для ботов и subprocess |
| Telegram         | **aiogram 3.x**           | Полностью асинхронный, зрелый, активно поддерживается          |
| БД               | **SQLite + aiosqlite**    | Не требует внешних сервисов, атомарные запросы, достаточно для однопользовательского режима |
| Конфиг           | **PyYAML + pydantic**     | YAML для человекочитаемости, pydantic для валидации            |
| Claude Code      | **CLI с `--output-format stream-json`** | Структурированный поток событий через stdout        |
| Управление зависимостями | **uv**             | Быстрый, современный                                          |

## 2. Структура проекта

```
pandemonium-bot/
├── pyproject.toml
├── config.example.yaml
├── src/
│   └── pandemonium/tgbot/
│       ├── __init__.py
│       ├── main.py              # Точка входа, запуск бота
│       ├── config.py            # Загрузка и валидация конфига (pydantic)
│       ├── db.py                # SQLite: схема, миграции, запросы
│       ├── bot/
│       │   ├── __init__.py
│       │   ├── handlers.py      # Обработчики команд и сообщений
│       │   ├── callbacks.py     # Обработчики inline-кнопок (Cancel, Allow/Deny)
│       │   ├── middleware.py    # Middleware авторизации
│       │   └── formatters.py   # Форматирование сообщений для Telegram
│       ├── claude/
│       │   ├── __init__.py
│       │   ├── process.py       # Управление процессом Claude Code
│       │   ├── events.py        # Парсинг stream-json событий
│       │   └── types.py         # Типы событий Claude Code
│       ├── session/
│       │   ├── __init__.py
│       │   ├── manager.py       # Управление сессиями
│       │   └── state.py         # Состояние сессии (FSM)
│       └── storage/
│           ├── __init__.py
│           └── protocol.py      # Запись протоколов в файловую систему
└── tests/
```

## 3. Компоненты

### 3.1 Config (`config.py`)

Pydantic-модели для валидации конфига при старте.

```python
class TelegramConfig(BaseModel):
    bot_token: str

class UserConfig(BaseModel):
    telegram_id: int
    name: str

class ProjectConfig(BaseModel):
    id: str
    name: str
    path: Path  # валидация: директория должна существовать

class StorageConfig(BaseModel):
    base_path: Path = Path("~/.pandemonium/sessions")

class TokenBudgetConfig(BaseModel):
    per_request_limit: int = 0  # 0 = без лимита

class AppConfig(BaseModel):
    telegram: TelegramConfig
    allowed_users: list[UserConfig]
    projects: list[ProjectConfig]
    storage: StorageConfig = StorageConfig()
    token_budget: TokenBudgetConfig = TokenBudgetConfig()
```

### 3.2 Database (`db.py`)

SQLite хранит оперативные данные: запросы, статусы, токены. Файловая система — протоколы (markdown).

#### Схема

```sql
CREATE TABLE requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    TEXT NOT NULL,
    user_id       INTEGER NOT NULL,
    request_number INTEGER NOT NULL,  -- инкремент в рамках проекта
    status        TEXT NOT NULL DEFAULT 'pending',
        -- pending | running | awaiting_input | completed | cancelled | error
    message_id    INTEGER,           -- ID сообщения-запроса в Telegram
    status_msg_id INTEGER,           -- ID статусного сообщения в Telegram
    chat_id       INTEGER,
    created_at    TEXT NOT NULL,
    completed_at  TEXT,
    tokens_input  INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    error_text    TEXT,
    UNIQUE(project_id, request_number)
);

CREATE TABLE interactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id    INTEGER NOT NULL REFERENCES requests(id),
    sub_number    INTEGER NOT NULL,  -- 1, 2, 3... → даёт N.1, N.2, N.3
    type          TEXT NOT NULL,     -- question | permission | chunk
    direction     TEXT NOT NULL,     -- from_claude | from_user
    content       TEXT NOT NULL,
    message_id    INTEGER,           -- ID сообщения в Telegram
    created_at    TEXT NOT NULL
);
```

Зачем БД если есть файлы:
- Быстрые выборки для `/history`, `/tokens`, `/status`.
- Связь Telegram message_id → request/interaction (для reply-маршрутизации).
- Атомарные обновления статуса.

Файлы — для долгосрочного хранения и человекочитаемых протоколов.

### 3.3 Claude Process (`claude/process.py`)

Обёртка над дочерним процессом Claude Code.

#### Запуск

```python
process = await asyncio.create_subprocess_exec(
    "claude",
    "--output-format", "stream-json",
    "--verbose",
    "--max-turns", "50",
    "-p", user_prompt,
    cwd=project_path,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

#### Поток событий (`claude/events.py`)

Claude Code с `--output-format stream-json` выдаёт JSON-объекты по одному на строку. Основные типы:

| Тип события       | Что содержит                          | Действие бота                        |
|-------------------|---------------------------------------|--------------------------------------|
| `assistant`       | Текстовый блок ответа                | Стриминг чанком пользователю         |
| `tool_use`        | Вызов инструмента (файл, bash, etc.) | Лог, опционально уведомление         |
| `tool_result`     | Результат инструмента                 | Лог                                  |
| `result`          | Финальный ответ + usage              | Отчёт + подсчёт токенов             |

Для permission-запросов и уточняющих вопросов — Claude Code пишет в stderr или использует специальные события. Парсер должен уметь различать:
- Запрос permission → кнопки Allow/Deny → ответ через stdin (`{"type":"permission","allowed":true}`)
- Уточняющий вопрос → текст пользователю → ответ через stdin

#### Класс ClaudeProcess

```python
class ClaudeProcess:
    """Управляет одним запущенным процессом Claude Code."""

    async def start(self, prompt: str, project_path: Path) -> None
    async def stream_events(self) -> AsyncIterator[ClaudeEvent]
    async def send_input(self, text: str) -> None
    async def send_permission(self, allowed: bool) -> None
    async def cancel(self) -> None       # SIGTERM → wait → SIGKILL
    async def wait(self) -> int          # return code
    def is_running(self) -> bool
```

### 3.4 Session Manager (`session/manager.py`)

Центральный координатор. Связывает Telegram-сообщения с процессами Claude Code.

#### Состояния сессии (`session/state.py`)

```
                ┌──────────┐
                │  IDLE    │ ← нет активного запроса
                └────┬─────┘
                     │ новый запрос
                     ▼
                ┌──────────┐
           ┌────│ RUNNING  │────┐
           │    └────┬─────┘    │
           │         │          │ ошибка/таймаут
     вопрос│         │завершён  │
           ▼         │          ▼
    ┌──────────────┐ │   ┌──────────┐
    │AWAITING_INPUT│ │   │  ERROR   │
    └──────┬───────┘ │   └──────────┘
           │ ответ   │
           └─────────┤
                     ▼
                ┌──────────┐
                │COMPLETED │
                └──────────┘
                ┌──────────┐
                │CANCELLED │ ← из RUNNING или AWAITING_INPUT
                └──────────┘
```

#### Ответственности

```python
class SessionManager:
    """Один экземпляр на приложение. В будущем — один на проект."""

    async def create_request(self, project_id: str, user_id: int,
                             chat_id: int, message_id: int,
                             prompt: str) -> int:
        """Создаёт запрос, запускает Claude Code. Возвращает request_number."""

    async def cancel_request(self, request_id: int) -> None
        """Отменяет активный запрос."""

    async def handle_user_reply(self, request_id: int, text: str) -> None
        """Передаёт ответ пользователя в Claude Code."""

    async def handle_permission_response(self, request_id: int,
                                          allowed: bool) -> None
        """Передаёт решение по permission."""
```

Внутри `create_request` запускается фоновая задача (`asyncio.Task`), которая:
1. Стартует `ClaudeProcess`.
2. Итерирует `stream_events()`.
3. Для каждого события — вызывает соответствующий callback (отправка в Telegram, запись в storage/DB).
4. При завершении — финализирует запрос.

### 3.5 Bot Layer (`bot/`)

#### Middleware авторизации (`middleware.py`)

Проверяет `message.from_user.id` против whitelist из конфига. Отклоняет неавторизованных.

#### Handlers (`handlers.py`)

```python
# /start — приветствие
# /status — статус текущего запроса
# /history — последние запросы из БД
# /tokens — суммарный расход из БД

# Текстовое сообщение (не команда, не reply):
#   → если есть активный запрос → "Подождите, запрос выполняется"
#   → иначе → SessionManager.create_request()

# Reply на сообщение-вопрос от бота:
#   → определить request_id по message_id из БД (interactions)
#   → SessionManager.handle_user_reply()
```

#### Callbacks (`callbacks.py`)

```python
# Cancel (callback_data: "cancel:{request_id}")
#   → SessionManager.cancel_request()

# Allow/Deny (callback_data: "perm:{request_id}:{allow|deny}")
#   → SessionManager.handle_permission_response()
```

### 3.6 Storage (`storage/protocol.py`)

Запись протоколов в файловую систему. Структура папок — как в requirements.md п. 6.1.

```python
class ProtocolStorage:
    def __init__(self, base_path: Path): ...

    async def save_request(self, project_id: str, number: int,
                           content: str) -> Path
    async def save_interaction(self, project_id: str, req_number: int,
                               sub_number: int, content: str,
                               is_response: bool) -> Path
    async def append_stream_log(self, project_id: str, req_number: int,
                                chunk: str) -> None
    async def save_report(self, project_id: str, req_number: int,
                          content: str) -> Path
    async def save_error(self, project_id: str, req_number: int,
                         error: str) -> Path
    async def save_meta(self, project_id: str, req_number: int,
                        meta: dict) -> Path
    def next_request_number(self, project_id: str) -> int
```

## 4. Потоки данных

### 4.1 Основной поток (запрос → ответ)

```
Пользователь                 Pandemonium (Bot)              SessionManager          ClaudeProcess
     │                          │                        │                       │
     │── текст запроса ────────►│                        │                       │
     │                          │── create_request() ───►│                       │
     │                          │                        │── start(prompt) ─────►│
     │◄── статус + [Cancel] ────│                        │                       │
     │                          │                        │                       │
     │                          │                        │◄── assistant event ───│
     │◄── чанк (reply) ────────│◄── send_chunk() ──────│                       │
     │                          │                        │                       │
     │                          │                        │◄── result event ──────│
     │◄── report.md (file) ────│◄── complete() ────────│                       │
     │◄── статус: Done ────────│                        │                       │
```

### 4.2 Поток с вопросом

```
Пользователь                 Pandemonium (Bot)              SessionManager          ClaudeProcess
     │                          │                        │                       │
     │                          │                        │◄── question event ────│
     │◄── вопрос (reply) ──────│◄── ask_user() ────────│      (ждёт stdin)     │
     │                          │   статус: AWAITING     │                       │
     │── reply на вопрос ──────►│                        │                       │
     │                          │── handle_reply() ─────►│                       │
     │                          │                        │── send_input() ──────►│
     │                          │                        │   статус: RUNNING     │
```

## 5. Стриминг и debounce

Claude Code с `stream-json` выдаёт события часто. Отправлять каждое как отдельное сообщение в Telegram нерационально (rate limit ~30 msg/sec, но UX плохой).

Стратегия:
1. Буфер накапливает текст из `assistant` событий.
2. Таймер (2-3 сек) срабатывает → содержимое буфера отправляется одним сообщением.
3. Если буфер переполнен (>4000 символов — лимит Telegram) → отправка немедленно.
4. При завершении → flush остатка буфера.

```python
class StreamBuffer:
    def __init__(self, flush_callback, interval=2.5, max_size=3500):
        self._buffer: list[str] = []
        self._flush_callback = flush_callback
        self._interval = interval
        self._max_size = max_size
        self._timer: asyncio.Task | None = None

    async def append(self, text: str) -> None
    async def flush(self) -> None
    async def close(self) -> None
```

## 6. Typing indicator

`asyncio.Task`, который в цикле вызывает `bot.send_chat_action(chat_id, "typing")` каждые 5 секунд, пока сессия в состоянии RUNNING или AWAITING_INPUT. Отменяется при завершении/отмене запроса.

## 7. Учёт токенов

Событие `result` от Claude Code содержит поле `usage`:

```json
{
  "type": "result",
  "result": "...",
  "usage": {"input_tokens": 15000, "output_tokens": 3200}
}
```

При `per_request_limit > 0`: промежуточные `assistant` события тоже содержат `usage`. Если сумма превышает лимит — вызов `ClaudeProcess.cancel()` и уведомление пользователю.

## 8. Обработка ошибок

| Ситуация                          | Действие                                              |
|-----------------------------------|-------------------------------------------------------|
| Claude Code exit code ≠ 0         | Читаем stderr, сохраняем error.md, шлём пользователю  |
| Таймаут (настраиваемый, default 30 мин) | SIGTERM → SIGKILL, уведомление, статус error   |
| Исключение в stream-парсере       | Логируем, уведомляем, завершаем процесс               |
| Telegram API ошибка               | Retry с exponential backoff (3 попытки)               |
| Перезапуск бота                    | При старте: все `running`/`awaiting_input` → `error`  |

## 9. Graceful shutdown

```python
async def shutdown(app: Application):
    # 1. Прекратить приём новых запросов
    # 2. Для каждой активной сессии:
    #    a. Отправить пользователю "Перезапуск ботаается"
    #    b. ClaudeProcess.cancel()
    #    c. Сохранить частичный протокол
    # 3. Закрыть БД
    # 4. Остановить бота
```

## 10. Подготовка к масштабированию

Решения, которые упрощают переход к мультипроектности:

- `SessionManager` индексирует сессии по `project_id` → легко держать по одной активной сессии на проект.
- `ProtocolStorage` уже разделяет папки по `project_id`.
- Таблица `requests` содержит `project_id` — запросы изолированы.
- `ClaudeProcess` не знает о Telegram — можно подключить другой фронтенд.

## 11. Зависимости

```toml
[project]
name = "pandemonium-bot"
requires-python = ">=3.12"

[project.dependencies]
aiogram = "^3.x"
aiosqlite = "^0.20"
pyyaml = "^6.0"
pydantic = "^2.x"
```
