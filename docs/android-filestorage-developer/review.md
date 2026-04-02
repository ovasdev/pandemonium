# Pandemonium Bot — Взгляд Android-разработчика (FileStorage2)

## Первое впечатление

Смотрю на Pandemonium с позиции человека, который каждый день пишет Kotlin/Compose и думает о lifecycle, background tasks и battery impact. Python-бот на сервере — другой мир. Но паттерны пересекаются больше, чем кажется.

## Что я узнаю из мобильной разработки

### SessionState — это ViewModel lifecycle

`SessionState` с переходами `IDLE → RUNNING → AWAITING_INPUT → COMPLETED/ERROR/CANCELLED` — это, по сути, sealed class UI state, который я использую в каждом ViewModel:

```kotlin
sealed class UiState {
    object Idle : UiState()
    object Loading : UiState()
    data class AwaitingInput(val question: String) : UiState()
    data class Success(val report: String) : UiState()
    data class Error(val message: String) : UiState()
}
```

Enum вместо sealed class — потому что Python. Но идея та же: конечный автомат с явными переходами. Нет boolean-флагов `isLoading`, `isError`, `isAwaiting`. Это правильно.

### StreamBuffer — это Flow с debounce

`StreamBuffer` с интервалом 2.5 секунды и порогом 3500 символов — это `Flow.debounce()` + `Flow.chunked()` в мире Kotlin coroutines. Паттерн знакомый: Claude генерирует данные быстрее, чем UI (Telegram) может их показать, нужен буфер. На Android у меня то же самое с WorkManager progress updates.

Разница: в Android я бы использовал `StateFlow` для hot updates, здесь — callback-паттерн с `flush_callback`. Оба варианта рабочие для своих экосистем.

### Typing indicator — это foreground notification

`_typing_loop` каждые 5 секунд отправляет `chat_action: typing`. Это прямой аналог foreground service notification на Android. Пользователь должен знать, что процесс жив. Без этого — тревога «завис?», отмена, повторный запрос. На Android это `ForegroundInfo` в WorkManager.

### Graceful shutdown — это onSaveInstanceState

При SIGTERM бот уведомляет пользователя, сохраняет частичный результат, убивает subprocess. На Android при `onSaveInstanceState` или `WorkManager.onStopped()` я делаю то же: сохраняю progress, чищу ресурсы, показываю notification.

`_recover_interrupted_requests` при старте — аналог `WorkManager.getWorkInfosByTag()`, проверка незавершённых задач и их восстановление/отмена.

## Что меня впечатлило

### Subprocess как Worker

`ClaudeProcess` — это, по сути, Worker в WorkManager:
- `start()` → `doWork()`
- `cancel()` → `onStopped()`
- `stream_events()` → `setProgress(Data)`
- `wait()` → `Result.success() / Result.failure()`

Чистая абстракция. Ничего лишнего. Если бы я писал Android-обёртку для CLI-процесса, структура была бы такой же.

### Token tracking как battery budget

`TokenBudgetConfig.per_request_limit` — лимит токенов на запрос с принудительной остановкой при превышении. Это тот же паттерн, что battery budget в Android: ресурс конечный, нужен enforcement. `_handle_token_limit` — аналог `BatteryManager.isCharging()` check перед heavy work.

### Файловый протокол

`ProtocolStorage` сохраняет каждый запрос в структурированную директорию. Я привык к Room для persistence, но для логов/протоколов файловая система — правильный выбор. Нет overhead базы данных, нет миграций, прямой доступ к файлам для отладки.

## Что бы я сделал иначе (с позиции мобильного разработчика)

### Offline resilience

Нет обработки ситуации, когда сеть к Telegram пропадает *во время* активной сессии. `telegram_retry` с 3 попытками — это для кратковременных сбоев. Но если бот потеряет связь с Telegram на 30 секунд, Claude продолжит работать, буфер переполнится, а пользователь ничего не увидит.

На Android я бы хранил pending messages в очереди и отправлял при восстановлении связи. Здесь аналог — `StreamBuffer` должен уметь складывать чанки в файл при недоступности Telegram и досылать их потом.

### Progress reporting

Сейчас пользователь видит typing indicator (жив) и stream chunks (промежуточные результаты). Но нет прогресс-бара: сколько инструментов вызвано, сколько файлов прочитано/изменено. В Android я бы добавил `setProgress(workDataOf("tools_used" to 5, "files_changed" to 3))`.

`ToolUseEvent` уже приходит, но игнорируется (`logger.info("Tool use: %s", tool)`). Можно считать инструменты и показывать: «Claude прочитал 12 файлов, изменил 3, запустил тесты...»

### Structured concurrency

`asyncio.create_task` без explicit scope — это как `GlobalScope.launch` в Kotlin. Работает, но при ошибке в дочерней задаче — нет гарантии propagation. `typing_task` и `process_task` создаются через `create_task` и чистятся в `_finalize`. Для текущего масштаба — нормально. Но в Kotlin structured concurrency (`viewModelScope`, `lifecycleScope`) гарантирует автоматическую отмену при смерти scope.

## Потенциал интеграции

Если завтра мне скажут «добавь в FileStorage2 Android отправку файлов боту через share intent»:

1. Android: Share → Intent → POST file to Telegram Bot API → caption с промптом
2. Pandemonium: `handle_document_message` уже обрабатывает файлы
3. Report → загрузить в FileStorage2 через API → показать в Marginalias

Инфраструктура готова. Нужен только API для загрузки отчётов (или использовать `$PANDEMONIUM_SEND_FILE` в обратную сторону).

## Резюме

Pandemonium использует те же паттерны, что и хороший Android-код: конечный автомат состояний, буферизация данных с debounce, graceful lifecycle management, resource budgeting. Код компактный, абстракции на правильном уровне. С точки зрения мобильного разработчика — это Worker, который работает на сервере вместо телефона, и это имеет смысл.
