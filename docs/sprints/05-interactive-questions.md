# Спринт 5 — Интерактивные вопросы и permissions

## Цель

Добавить обработку двух типов промежуточных вопросов от Claude Code: запросы разрешений (permission) и уточняющие вопросы. Пользователь отвечает через Telegram, ответы передаются обратно в Claude Code.

## Задачи

### 5.1 Исследование формата событий

Перед реализацией — изучить, как именно Claude Code с `--output-format stream-json` сигнализирует:
- Запрос permission (какой тип события, какие поля).
- Уточняющий вопрос (ожидание stdin).

Зафиксировать формат в комментариях / docstring в `claude/events.py`.

> Примечание: если Claude Code не различает эти типы в stream-json, возможно потребуется парсинг stderr или использование `--permission-mode` флагов. Решение принимается на этапе исследования.

### 5.2 Расширение парсера событий (`claude/events.py`)

Добавить типы:

```python
@dataclass
class PermissionRequestEvent:
    tool: str
    description: str   # что именно хочет сделать Claude

@dataclass
class InputRequestEvent:
    question: str      # текст вопроса от Claude
```

Обновить `parse_event()` для распознавания этих типов.

### 5.3 SessionManager — обработка вопросов

Расширить `_run_session`:

При `PermissionRequestEvent`:
1. Flush stream buffer.
2. Состояние → `AWAITING_INPUT`.
3. Увеличить `sub_counter`.
4. Сохранить вопрос: `storage.save_interaction(N, sub, content, is_response=False)`.
5. Записать interaction в БД (type="permission", direction="from_claude").
6. Отправить пользователю сообщение с текстом + кнопки **Allow** / **Deny**.
7. Ждать ответа (через `asyncio.Event` или `asyncio.Future` в ActiveSession).

При `InputRequestEvent`:
1. Аналогично, но без кнопок — просто сообщение с вопросом.
2. Ждать текстовый reply от пользователя.

Новые методы SessionManager:

```python
async def handle_permission_response(self, request_id: int,
                                      allowed: bool) -> None:
    # 1. Записать ответ в storage и БД
    # 2. claude_process.send_permission(allowed)  — или send_input("y"/"n")
    # 3. Состояние → RUNNING
    # 4. Разблокировать ожидание (future.set_result)

async def handle_user_reply(self, request_id: int, text: str) -> None:
    # 1. Записать ответ в storage и БД
    # 2. claude_process.send_input(text)
    # 3. Состояние → RUNNING
    # 4. Разблокировать ожидание
```

### 5.4 Механизм ожидания ответа

В `ActiveSession` добавить:

```python
pending_response: asyncio.Future | None = None
```

В `_run_session` при вопросе:
```python
session.pending_response = asyncio.get_event_loop().create_future()
await session.pending_response  # блокирует цикл событий сессии
session.pending_response = None
```

В `handle_user_reply` / `handle_permission_response`:
```python
session.pending_response.set_result(response)
```

### 5.5 Обработчики бота

**callbacks.py** — обработчик кнопок Allow/Deny:
- Callback data: `perm:{request_id}:allow` / `perm:{request_id}:deny`.
- Вызов `SessionManager.handle_permission_response()`.
- Обновить сообщение: убрать кнопки, показать выбор пользователя.

**handlers.py** — обработчик reply на вопрос:
- Определить, что сообщение — reply на вопрос от бота.
- Найти interaction в БД по `message_id` reply-target.
- Определить `request_id`.
- Вызов `SessionManager.handle_user_reply()`.

### 5.6 Протоколирование

Каждый вопрос и ответ записывается:
- `N.{sub}.md` — вопрос от Claude.
- `N.{sub}.response.md` — ответ пользователя.
- В БД: запись в `interactions` с type + direction.

## Критерий готовности

- Permission-запросы отображаются с кнопками Allow/Deny.
- Нажатие кнопки передаёт решение в Claude Code, процесс продолжается.
- Уточняющие вопросы отображаются как сообщения.
- Reply пользователя передаётся в Claude Code.
- Все вопросы/ответы записаны в файлы и БД с корректной суб-нумерацией.
- После ответа на вопрос — сессия возвращается в RUNNING и продолжает стриминг.
