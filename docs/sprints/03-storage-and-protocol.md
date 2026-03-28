# Спринт 3 — Протоколирование и Storage

## Цель

Реализовать `ProtocolStorage` — запись всех данных сессии в файловую систему, а также функции работы с БД для запросов и взаимодействий.

## Задачи

### 3.1 ProtocolStorage (`storage/protocol.py`)

Реализовать класс согласно `architecture.md` п. 3.6:

```python
class ProtocolStorage:
    def __init__(self, base_path: Path): ...

    def next_request_number(self, project_id: str) -> int
    async def save_request(self, project_id: str, number: int, content: str) -> Path
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
```

Структура папок:
```
{base_path}/{project_id}/{request_N}/
    request.md, N.1.md, N.1.response.md, stream_log.md, report.md, error.md, meta.json
```

- `next_request_number` — сканирует существующие папки, возвращает max+1.
- Все write-операции — `aiofiles` или `asyncio.to_thread(Path.write_text, ...)`.
- Папки создаются автоматически (`mkdir(parents=True, exist_ok=True)`).

### 3.2 DB-функции для requests (`db.py` — расширение)

Добавить функции:

```python
async def create_request(db, project_id, user_id, request_number,
                         message_id, status_msg_id, chat_id) -> int
async def update_request_status(db, request_id, status, **kwargs) -> None
async def get_active_request(db, project_id) -> Row | None
async def get_request_by_status_msg(db, status_msg_id) -> Row | None
async def get_recent_requests(db, project_id, limit=10) -> list[Row]
async def get_token_totals(db, project_id) -> dict
```

### 3.3 DB-функции для interactions (`db.py` — расширение)

```python
async def create_interaction(db, request_id, sub_number, type,
                             direction, content, message_id) -> int
async def get_interaction_by_message(db, message_id) -> Row | None
async def get_next_sub_number(db, request_id) -> int
```

### 3.4 Тесты

Unit-тесты:
- `ProtocolStorage`: создание папок, запись файлов, нумерация.
- DB-функции: CRUD, корректность статусов.

## Критерий готовности

- Протоколы записываются в правильную структуру папок.
- Нумерация инкрементируется корректно.
- DB-функции работают, статусы обновляются.
- meta.json содержит корректные данные.
