# Спринт 4 — SessionManager и основной поток

## Цель

Реализовать `SessionManager` и связать все компоненты: пользователь пишет запрос → бот запускает Claude Code → стримит чанки → возвращает отчёт. Без интерактивных вопросов (только прямой поток).

## Задачи

### 4.1 StreamBuffer (`session/buffer.py`)

Буфер для debounce стриминга (согласно `architecture.md` п. 5):

```python
class StreamBuffer:
    def __init__(self, flush_callback: Callable[[str], Awaitable],
                 interval: float = 2.5, max_size: int = 3500):
        ...

    async def append(self, text: str) -> None
    async def flush(self) -> None
    async def close(self) -> None
```

- `append` — добавляет текст в буфер. Если размер > max_size — немедленный flush. Иначе — перезапускает таймер.
- Таймер — `asyncio.Task` с `asyncio.sleep(interval)` → flush.
- `close` — flush остатка, отмена таймера.

### 4.2 Session state (`session/state.py`)

Enum состояний и dataclass активной сессии:

```python
class SessionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"

@dataclass
class ActiveSession:
    request_id: int
    request_number: int
    project_id: str
    chat_id: int
    user_message_id: int
    status_message_id: int
    state: SessionState
    claude_process: ClaudeProcess
    stream_buffer: StreamBuffer
    typing_task: asyncio.Task | None
    process_task: asyncio.Task | None
    sub_counter: int = 0
```

### 4.3 SessionManager (`session/manager.py`)

```python
class SessionManager:
    def __init__(self, config: AppConfig, db, storage: ProtocolStorage,
                 bot: Bot): ...

    async def create_request(self, project_id, user_id, chat_id,
                             message_id, prompt) -> int

    async def cancel_request(self, request_id) -> None
```

`create_request`:
1. Проверяет нет ли активной сессии → если есть, отклоняет.
2. Получает `next_request_number` из storage.
3. Сохраняет запрос в БД и файловую систему.
4. Создаёт `ClaudeProcess`, `StreamBuffer`, `ActiveSession`.
5. Запускает `_run_session()` как `asyncio.Task`.

`_run_session` (приватный метод — основной цикл):
1. Запускает typing indicator task.
2. Итерирует `claude_process.stream_events()`.
3. `AssistantEvent` → `stream_buffer.append(text)` + `storage.append_stream_log()`.
4. `ResultEvent` → flush buffer, сохранить report, обновить токены в БД, отправить файл, обновить статус.
5. При ошибке / exit code ≠ 0 → сохранить error, уведомить.
6. Финализация: остановить typing task, закрыть buffer, записать meta.json.

### 4.4 Обработчики бота (расширение `handlers.py`)

- Текстовое сообщение (не команда) → `SessionManager.create_request()`.
- Перед запуском → бот отправляет статусное сообщение с кнопкой Cancel.
- flush_callback для StreamBuffer → `bot.send_message(chat_id, chunk, reply_to=user_message_id)`.

### 4.5 Callbacks (расширение `callbacks.py`)

- `cancel:{request_id}` → `SessionManager.cancel_request()`.

### 4.6 Typing indicator

Фоновая задача:
```python
async def _typing_loop(self, chat_id: int):
    while True:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(5)
```

Отменяется при завершении сессии.

### 4.7 Форматирование (`bot/formatters.py`)

- `format_status_message(request_number, state)` → текст для статусного сообщения.
- `format_error_message(error_text)` → текст ошибки.

## Критерий готовности

- Пользователь пишет запрос → бот отвечает статусом с кнопкой Cancel.
- Видно typing пока Claude работает.
- Чанки приходят отдельными сообщениями с debounce.
- Финальный отчёт приходит как .md файл.
- Cancel останавливает процесс, статус обновляется.
- Ошибки Claude Code → сообщение пользователю.
- Всё протоколируется в файловой системе и БД.
