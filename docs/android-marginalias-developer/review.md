# Pandemonium Bot — Взгляд Android-разработчика (Marginalias)

## Контекст

Я разрабатываю Marginalias Android — клиент для просмотра файлов с нескольких серверов, комментариев, Den-хранилища. Мой код — это Kotlin/Compose, Hilt, Retrofit, dynamic server URLs. Pandemonium — Python, asyncio, subprocess. Но у нас общий UX-контекст: оба работают как клиенты к внешним сервисам, оба стримят данные пользователю, оба должны обрабатывать разрывы и таймауты.

## Что меня зацепило

### Multi-server pattern

В Marginalias Android я работаю с несколькими серверами FileStorage2 — динамические URL, разные API ключи, переключение между ними. В Pandemonium — аналогичная задача: несколько проектов, каждый со своим path, переключение через `/projects`.

`SessionManager.set_active_project()` сбрасывает персону и session ID при смене проекта. Это правильно — контекст Claude Code привязан к проекту. В Marginalias я делаю то же: при смене сервера сбрасываю кеш, реинициализирую Retrofit instance, чищу пагинацию.

Но в Pandemonium переключение — глобальное. Один активный проект на весь бот. В Marginalias пользователь видит файлы с разных серверов одновременно (через табы). Если Pandemonium когда-то захочет поддержать «спроси Claude в контексте проекта А, пока работает запрос к проекту Б» — текущая архитектура не позволит.

### Reply chain как thread context

`_build_reply_context` — сборка цепочки реплаев до 2 уровней. В Marginalias у меня threaded comments: комментарий → ответ → ответ на ответ. Тот же паттерн — построить контекст разговора для отображения.

Глубина 2 — разумный лимит. В комментариях Marginalias я тоже ограничиваю nesting до 3 уровней, потому что на мобильном экране глубже — нечитаемо. Для промпта Claude — те же ограничения по размеру контекста.

### Callback routing и deep links

`callback_data` вроде `perm:42:allow`, `project:my-app`, `persona:developer` — это, по сути, deep linking. В Marginalias Android у меня:
```
marginalias://server/{serverId}/file/{fileId}
marginalias://server/{serverId}/file/{fileId}/comments
```

Парсинг `callback.data.split(":")` — аналог NavArgs. Работает, но хрупко: нет типизации, нет валидации формата на уровне типов. В Kotlin я использую `@Serializable` для NavArgs. Здесь — строковый split. Для трёх типов callbacks — достаточно. При десяти — стоит ввести typed callback data.

## Что я вижу через призму Marginalias

### Отчёты как файлы

`_handle_result` отправляет финальный отчёт как `BufferedInputFile` — markdown-документ. Это файл. А файлы — моя тема.

Представь: отчёт Claude автоматически загружается в FileStorage2, получает теги (`pandemonium`, `project:my-app`, дату), и появляется в Marginalias. Пользователь может:
- Читать отчёт с syntax highlighting (у нас есть code renderer)
- Оставлять комментарии к конкретным строкам
- Искать по старым отчётам через полнотекстовый поиск
- Группировать по проектам и датам

Команда `/wiki` уже загружает файлы в Marginalias с тегами. Паттерн проложен. Осталось применить его к отчётам Claude.

### Stream log как live document

`stream_log.md` — лог стриминга — растёт в реальном времени. В Marginalias у меня есть file renderers: markdown, code, image, video, PDF. Если stream log доступен по URL, его можно рендерить live — как tail -f, но в браузере с markdown formatting.

### Загрузка файлов через Telegram

`handle_document_message` и `handle_photo_message` скачивают файл в `uploads/`, формируют prompt с путём. Если бы загруженный файл параллельно уходил в FileStorage2, пользователь мог бы потом найти его в Marginalias, даже если Claude ничего с ним не сделал.

## Технические заметки

### Typing indicator и пагинация

В Marginalias я показываю skeleton/shimmer при загрузке данных. В Pandemonium — `chat_action: typing` каждые 5 секунд. Обе стратегии решают одну задачу: «система жива, подожди». Но typing indicator в Telegram — binary (есть/нет). Нет промежуточных состояний. В мобильном UI я могу показать progress bar, количество загруженных элементов, ETA. Telegram этого не позволяет — это ограничение платформы, а не кода.

### Race condition при permission response

`handle_permission_response` проверяет `session.state != SessionState.AWAITING_INPUT` перед обработкой. Но что если пользователь нажмёт Allow, а session уже перешла в ERROR (таймаут)? Future будет отменён, но кнопки Allow/Deny останутся видимыми. В Marginalias у меня та же проблема с stale UI — решаю через invalidation при изменении состояния.

Здесь `callback.message.edit_reply_markup(reply_markup=None)` убирает кнопки *после* нажатия. Но не убирает при таймауте/ошибке. Стоит добавить cleanup кнопок в `_handle_error`.

### YAML конфиг vs Hilt DI

`config.yaml` + `AppConfig` — это manual dependency injection. В Kotlin я использую Hilt с `@Provides` модулями. Разная экосистема, но задача та же: собрать зависимости, провалидировать, раздать. `dp["config"] = config` — это service locator pattern, как `Hilt.get<Config>()`, только без compile-time safety.

## Резюме

Pandemonium и Marginalias Android — разные технологии, но общие паттерны: multi-source switching, threaded context, file-centric workflow, live updates. Точка пересечения очевидна — отчёты Claude как файлы в FileStorage2/Marginalias. Код бота готов к этой интеграции: файлы уже генерируются, upload pipeline уже работает (`/wiki`). Нужно только подключить отчёты к тому же потоку.
