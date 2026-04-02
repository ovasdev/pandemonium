# Pandemonium Bot — Взгляд Database Admin

## Первое впечатление

После PostgreSQL с Diesel migrations, RLS policies, pgvector и multi-tenant isolation — SQLite на aiosqlite выглядит как блокнот рядом с Excel. Но это не критика. Это правильный инструмент для задачи.

## Схема данных

### Две таблицы

```sql
CREATE TABLE requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     TEXT NOT NULL,
    user_id        INTEGER NOT NULL,
    request_number INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    message_id     INTEGER,
    status_msg_id  INTEGER,
    chat_id        INTEGER,
    created_at     TEXT NOT NULL,
    completed_at   TEXT,
    tokens_input   INTEGER DEFAULT 0,
    tokens_output  INTEGER DEFAULT 0,
    error_text     TEXT,
    UNIQUE(project_id, request_number)
);

CREATE TABLE interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  INTEGER NOT NULL REFERENCES requests(id),
    sub_number  INTEGER NOT NULL,
    type        TEXT NOT NULL,
    direction   TEXT NOT NULL,
    content     TEXT NOT NULL,
    message_id  INTEGER,
    created_at  TEXT NOT NULL
);
```

Минимальная, но функциональная схема. Две таблицы, одна foreign key. Для бота, обслуживающего одного пользователя — это ровно тот уровень нормализации, который нужен.

### Что сделано хорошо

**UNIQUE constraint на `(project_id, request_number)`** — предотвращает дубли. Правильно.

**Temporal columns** — `created_at` и `completed_at` хранятся как TEXT в ISO 8601. Для SQLite это стандарт — нет нативного TIMESTAMP типа. `_now()` генерирует UTC ISO — consistent и sortable.

**Soft status через TEXT** — `status` как `TEXT NOT NULL DEFAULT 'pending'` вместо enum. SQLite не поддерживает ENUMs, CHECK constraint был бы вариантом, но для бота — излишне. Python-side enum `SessionState` обеспечивает валидность.

**Foreign key** — `interactions.request_id REFERENCES requests(id)`. Но SQLite по дефолту не enforce foreign keys без `PRAGMA foreign_keys = ON`. В `init_db` этого pragma нет. FK constraint существует только декларативно — orphan interactions возможны при ручном удалении requests.

### Что бы я улучшил

**1. Индексы.** Ни одного явного индекса. Текущие запросы:

| Query | Scan type |
|-------|-----------|
| `WHERE project_id = ? AND status IN (...)` | full table scan |
| `WHERE status_msg_id = ?` | full table scan |
| `WHERE project_id = ? ORDER BY id DESC` | full table scan |
| `WHERE message_id = ?` (interactions) | full table scan |

При 100 запросах — незаметно. При 10,000 — замедление. Рекомендую:

```sql
CREATE INDEX idx_requests_project_status ON requests(project_id, status);
CREATE INDEX idx_requests_status_msg ON requests(status_msg_id);
CREATE INDEX idx_interactions_message ON interactions(message_id);
CREATE INDEX idx_interactions_request ON interactions(request_id);
```

**2. `PRAGMA foreign_keys = ON`.** Добавить в `init_db` после `connect`. Иначе FK — декорация.

**3. `PRAGMA journal_mode = WAL`.** Write-Ahead Logging улучшает concurrent read performance. Для asyncio с одним writer — не критично, но стандартная best practice для SQLite.

**4. CHECK constraint на status:**

```sql
CHECK(status IN ('pending', 'running', 'awaiting_input', 'completed', 'cancelled', 'error'))
```

Не обязательно, но защищает от опечаток при прямом SQL.

## Паттерны доступа к данным

### SQL в строках

Все запросы — inline SQL strings в функциях `db.py`. Нет ORM, нет query builder. Для двух таблиц и десяти запросов — правильный выбор. ORM (SQLAlchemy, Tortoise) добавил бы слой абстракции без реальной пользы.

### `update_request_status` — dynamic SQL

```python
for col in ("tokens_input", "tokens_output", "error_text"):
    if col in kwargs:
        sets.append(f"{col} = ?")
        values.append(kwargs[col])
```

Dynamic column list через kwargs. Потенциальный SQL injection? Нет — column names hardcoded в tuple, values параметризованы. Безопасно. Но стоит отметить: если кто-то добавит новую колонку и забудет обновить tuple — значение молча проигнорируется. Explicit kwargs (`tokens_input: int | None = None, ...`) были бы safer.

### `aiosqlite.Row` factory

`db.row_factory = aiosqlite.Row` — доступ по имени колонки (`row["status"]`). Правильно. Без этого — доступ по индексу, что хрупко при изменении схемы.

### Отсутствие миграций

Схема создаётся через `CREATE TABLE IF NOT EXISTS` при каждом запуске. Нет системы миграций. Добавить колонку = ручной `ALTER TABLE` или пересоздание базы.

Для Pandemonium это приемлемо: данные в SQLite — операционные, не персистентные. Протоколы хранятся в файловой системе. Потерять SQLite — потерять историю и счётчики, но не отчёты.

Если нужны миграции — `alembic` с SQLite или просто `_SCHEMA_VERSION` + manual ALTER TABLE. Но сейчас это premature.

## Дуальность хранения

В Pandemonium данные хранятся дважды:
1. **SQLite** — status tracking, token accounting, message IDs
2. **Файловая система** (`ProtocolStorage`) — request text, stream log, report, meta

Это осознанная денормализация. SQLite — для запросов (`get_recent_requests`, `get_token_totals`). Файлы — для полного протокола и отладки. Дублирование минимальное: SQLite не хранит полный текст запроса/ответа.

В FileStorage2 у нас тоже dual storage: PostgreSQL (метаданные) + MinIO (файлы). Тот же паттерн, другой масштаб.

## Concurrency

SQLite с aiosqlite — один writer, multiple readers. `await db.commit()` после каждой write-операции. Нет транзакций, объединяющих несколько writes.

Потенциальная проблема: `create_request` делает INSERT + COMMIT, потом `update_request_status` делает UPDATE + COMMIT. Между ними — промежуток, где request существует со статусом `pending`, но session уже `RUNNING`. При крэше в этот промежуток — inconsistency. Для production — обернуть в одну транзакцию. Для текущего масштаба — не критично.

### Token aggregation

`get_token_totals` считает `SUM(tokens_input)` и `SUM(tokens_output)` по всем requests проекта. При 10,000 requests — один full scan. Кешировать в отдельной таблице (`project_token_totals`) при высокой нагрузке. Сейчас — излишне.

## Сравнение с FileStorage2

| Аспект | Pandemonium | FileStorage2 |
|--------|------------|--------------|
| СУБД | SQLite (aiosqlite) | PostgreSQL (Diesel) |
| Миграции | Нет | Diesel migrations |
| ORM | Нет (raw SQL) | Diesel (Rust ORM) |
| Multi-tenant | Нет (single user) | RLS policies |
| Full-text search | Нет | pg_trgm |
| Vector search | Нет | pgvector |
| Transactions | Per-statement | Per-request |
| Backup | Копировать файл | pg_dump |

Pandemonium на правильном уровне: задача не требует PostgreSQL. SQLite — embedded, zero config, единственная зависимость — файл.

## Рекомендации

1. **Индексы** — 4 строки SQL, мгновенный эффект при росте данных
2. **`PRAGMA foreign_keys = ON`** — одна строка, правильность FK
3. **`PRAGMA journal_mode = WAL`** — одна строка, лучше concurrent reads
4. **Explicit kwargs в `update_request_status`** — type safety вместо `**kwargs`
5. **Backup скрипт** — `cp pandemonium.db pandemonium.db.bak` по cron (SQLite backup API ещё лучше)

## Резюме

SQLite в Pandemonium — правильный выбор для масштаба задачи. Схема минимальная, запросы корректные, параметризация на месте. Основные замечания: нет индексов, нет FK enforcement, нет WAL mode. Всё исправляется за 10 минут. Миграции и ORM — не нужны при текущем размере. Dual storage (SQLite + файлы) — грамотный дизайн: каждое хранилище делает то, что умеет лучше.
