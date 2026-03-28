# Критические особенности и подводные камни

## 1. Env vars для дочернего процесса claude

Дочерние процессы `claude` наследуют переменные окружения `CLAUDECODE` и `CLAUDE_CODE_ENTRYPOINT`, из-за чего думают, что запущены как вложенные.

**Решение:** `ClaudeProcess.start()` фильтрует эти переменные из env. `start.sh` тоже их unset-ит.

## 2. --output-format stream-json требует --verbose

Без `--verbose` Claude Code выходит с ошибкой в stderr, stdout пуст.
Команда запуска должна содержать оба флага: `--print` И `--verbose`.

## 3. Pydantic v2: field_validator не работает на default values

`@field_validator` в pydantic v2 НЕ вызывается для значений по умолчанию.
`StorageConfig` использует И validator, И `model_post_init` для expanduser.

## 4. Конструкторы исключений aiogram

```python
TelegramNetworkError(method, message)      # method — обязательный первый аргумент
TelegramRetryAfter(method, message, retry_after)
```

В тестах используется `MagicMock()` как fake method.

## 5. Формат событий permission/input

Определён как:
```json
{"type": "system", "subtype": "permission_request", "tool": "...", "description": "..."}
{"type": "system", "subtype": "input_request", "question": "..."}
```

Ответ на permission:
```json
{"type": "permission", "allowed": true/false}
```

Если реальный Claude Code использует другой формат — нужно обновить `events.py`.

## 6. Future-based waiting

`pending_response: asyncio.Future` создаётся для каждого permission/input request.
Разрешается через `.set_result()`, отменяется при отмене процесса.
Нельзя подавлять `CancelledError` — нарушит shutdown.

## 7. stdin = DEVNULL

`ClaudeProcess` создаёт subprocess с `stdin=DEVNULL`.
`send_input()` и `send_permission()` по факту не работают через stdin —
это заглушки, подготовленные для будущей интеграции через другой механизм.

## 8. --permission-mode bypassPermissions

Текущая реализация запускает claude с `--permission-mode bypassPermissions`,
что автоматически разрешает все операции. Permission request flow в коде готов,
но на практике не триггерится при этом режиме.

## 9. Markdown → HTML конвертация

`markup.py` — собственная реализация md→HTML для Telegram.
Telegram поддерживает ограниченное подмножество HTML.
При ошибке парсинга HTML fallback на plain text.

## 10. Rate limiting

- StreamBuffer (2.5s debounce, 3500 char threshold) — защита от Telegram rate limit
- telegram_retry() — exponential backoff при TelegramNetworkError
- token_budget.per_request_limit — лимит токенов на запрос (0 = без лимита)
