# Схема базы данных

Файл: `~/.pandemonium/sessions/pandemonium.db` (SQLite, async через aiosqlite)

## Таблица `requests`

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER PK AUTOINCREMENT | |
| project_id | TEXT NOT NULL | ID проекта из конфига |
| user_id | INTEGER NOT NULL | Telegram user ID |
| request_number | INTEGER NOT NULL | Порядковый номер в проекте |
| status | TEXT DEFAULT 'pending' | pending → running → completed/cancelled/error; или → awaiting_input → running |
| message_id | INTEGER | Telegram msg ID оригинального запроса |
| status_msg_id | INTEGER | Telegram msg ID статусного сообщения (с кнопкой Cancel) |
| chat_id | INTEGER | Telegram chat ID |
| created_at | TEXT | ISO UTC timestamp |
| completed_at | TEXT | ISO UTC, заполняется при terminal-статусе |
| tokens_input | INTEGER DEFAULT 0 | |
| tokens_output | INTEGER DEFAULT 0 | |
| error_text | TEXT | Текст ошибки (nullable) |

**UNIQUE** constraint: `(project_id, request_number)`

### Статусы запроса

```
pending → running → completed
                  → cancelled
                  → error
         running → awaiting_input → running (loop)
```

## Таблица `interactions`

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER PK AUTOINCREMENT | |
| request_id | INTEGER FK → requests.id | |
| sub_number | INTEGER | 1, 2, 3... для нумерации N.1, N.2, N.3 |
| type | TEXT | `question`, `permission`, `internal` |
| direction | TEXT | `from_claude` или `from_user` |
| content | TEXT | Полный текст вопроса/ответа |
| message_id | INTEGER | Telegram msg ID (nullable) |
| created_at | TEXT | ISO UTC timestamp |
