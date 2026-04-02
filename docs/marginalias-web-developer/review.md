# Pandemonium Bot — Взгляд веб-разработчика Marginalias

## Контекст

Я делаю Marginalias web — React 19, TypeScript, TanStack Query, Zustand. Rich file renderers: markdown с подсветкой, код, изображения, видео, PDF. Threaded comments. Read-focused UI. Pandemonium — серверный Python-бот, но я вижу здесь потенциального поставщика контента для моего интерфейса.

## Что мне знакомо

### Markdown rendering pipeline

`md_to_telegram_html` — мой конёк. Конвертация markdown в presentation format. Только у меня цель — React-компоненты с syntax highlighting через Shiki, а здесь — подмножество HTML для Telegram (`<b>`, `<i>`, `<code>`, `<pre>`).

Текущая реализация в `markup.py` — это regex-based конвертер. Работает для Claude output, но есть edge cases:
- Nested formatting (`**bold _italic_ bold**`) не обрабатывается
- Code blocks внутри списков сломаются
- HTML entities в коде могут конфликтовать с Telegram-парсером

В Marginalias я использую unified/remark pipeline для markdown AST → React. Это heavy, но корректно. Для Telegram regex — оправданный компромисс: AST-парсер для подмножества из 6 тегов — overkill.

### Truncation

`truncate_html` режет HTML по символам и пытается не сломать теги. Это знакомая боль: в Marginalias я truncate markdown для превью файлов в списке. Текущая реализация — наивная (поиск последнего `<` и `>`), но для Telegram 4096 символов — работает. Мне с 280-символьными превью сложнее.

### Callback routing = client-side routing

Фронтенд-разработчик уже писал об этом, но я добавлю деталь. В Marginalias у меня:

```typescript
/files/:fileId → FileView
/files/:fileId/comments → CommentsPanel
/files/:fileId/comments/:commentId → CommentThread
```

В Pandemonium:
```
perm:{request_id}:{action}
project:{project_id}
persona:{persona_name}
qrand:{count}:{from}:{to}
```

Это буквально URL routing, только serialized в строку через `:`. В React Router я бы сделал typed route params. Здесь — `split(":")`. Для 4 типов callbacks — нормально. При росте — стоит ввести парсер с валидацией.

## Что я вижу как потребитель данных

### Отчёты Claude — это файлы для Marginalias

`_handle_result` генерирует `report_{N}.md` и отправляет через Telegram. Этот же файл — идеальный кандидат для рендеринга в Marginalias:

- **Markdown renderer** — у меня уже есть, с подсветкой синтаксиса, таблицами, ссылками
- **Code blocks** — Shiki подсветит любой язык, который Claude упоминает в fenced blocks
- **Threaded comments** — пользователь может комментировать конкретные части отчёта
- **Versioning** — если Claude переделывает задачу, старые и новые отчёты можно сравнивать

`/wiki` уже показывает, что pipeline «создать файл → загрузить в FileStorage2 → тегировать» работает. Для отчётов — тот же путь.

### Stream log как live view

`stream_log.md` — append-only лог стриминга. Если его отдавать по WebSocket (или даже SSE), я могу показать live rendering:

```typescript
const { data } = useQuery({
  queryKey: ['stream', requestId],
  refetchInterval: 2000, // poll каждые 2 сек
})
return <MarkdownRenderer content={data} />
```

Или лучше — WebSocket с TanStack Query subscription. Realtime-обновление markdown в браузере, с подсветкой синтаксиса. Это то, что Telegram не может: rich rendering in real time.

### Session history как коллекция

`ProtocolStorage` хранит сессии в структурированных директориях: `{project_id}/request_{N}/`. Каждая сессия — это набор файлов. В Marginalias «коллекция» — это группа файлов с общим тегом. Sessions → Collections — естественный маппинг.

UI в Marginalias:
- Список сессий (с фильтрацией по проекту, статусу, дате)
- Каждая сессия раскрывается: request, stream log, report, interactions
- Статистика токенов — графики (у меня есть chart components)
- Поиск по тексту отчётов (полнотекстовый поиск через API)

### Meta.json как structured data

`meta.json` с токенами и статусами — это metadata, которую Marginalias может отобразить в sidebar:

```json
{
  "request_number": 42,
  "status": "completed",
  "tokens_used": { "input": 15000, "output": 8000, "total": 23000 }
}
```

В Marginalias sidebar показывает метаданные файла (размер, дата, теги). Для отчётов — добавить tokens, duration, project, persona.

## Технические наблюдения

### HTML escaping

`md_to_telegram_html` сначала извлекает code blocks, потом escapes остальной текст, потом применяет regex. Порядок правильный — code blocks защищены от double-escaping. В React я использую `dangerouslySetInnerHTML` только для trusted content. Здесь аналог — все пользовательские данные проходят через `html.escape()`.

### Retry strategy

`telegram_retry` с exponential backoff и `TelegramRetryAfter` handling. В TanStack Query у меня:

```typescript
retry: 3,
retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
```

Тот же паттерн. Но TanStack Query делает это декларативно на уровне query конфигурации. Здесь — императивный wrapper. Оба работают.

### Отсутствие кеширования

В Pandemonium нет кеша. Каждый запрос к Claude — свежий subprocess. Для LLM это нормально: одинаковый промпт не гарантирует одинаковый результат. Но для Telegram API calls (получение bot info, файлов) кеширование бы не помешало.

В Marginalias я кеширую всё через TanStack Query: файлы, теги, комментарии, с stale-while-revalidate. Разные домены — разные стратегии.

## Резюме

Pandemonium генерирует ровно тот контент, который Marginalias умеет красиво показывать: markdown-отчёты, structured metadata, session history. Текущий delivery — через Telegram (plain text + файл). Добавив upload в FileStorage2, мы получим полноценный UI для AI-assisted development: rich rendering, comments, search, history, analytics. Код бота к этому готов — нужен только transport layer.
