---
name: filestorage-search
description: "Поиск файлов в filestorage2 на Raspberry Pi и отправка найденных файлов пользователю с подписью-метаданными. Активируется на: 'найди файл', 'поищи в хранилище', 'что есть по теме', 'покажи файлы с тегом', 'файлы в коллекции', 'отправь файл из хранилища', 'скачай с малинки'. НЕ применяется к локальному pandemonium.filestorage — для этого скил pandemonium-filestorage."
metadata:
  author: alyx
  version: "1.0.0"
related:
  - filestorage2-api
  - pandemonium-filestorage
---

# Поиск файлов в filestorage2

Скил для поиска файлов на удалённом filestorage2 сервере (Raspberry Pi) и отправки найденных файлов пользователю в Telegram с подписью, содержащей метаданные.

## Конфигурация

| Параметр | Значение |
|----------|---------|
| BASE_URL | `http://192.168.1.105:4733` |
| API_KEY  | `$RASPBERY_FILESTORAGE_KEY` (env) |

Все curl-запросы: `Authorization: Bearer $RASPBERY_FILESTORAGE_KEY`.

## Клиент: MCP (предпочтительно) или curl

Сервер `filestorage2` зарегистрирован как MCP в user-scope Claude Code — инструменты `mcp__filestorage2__*`. Предпочитай их над curl:

| Задача | MCP tool |
|--------|----------|
| Полнотекстовый поиск | `search_files(q, limit)` |
| Список файлов с фильтрами | `list_files(tag_ids, collection_ids, type, ...)` |
| Список тегов | `list_tags` |
| Список коллекций | `list_collections` |
| Метаданные файла | `get_file_info(file_id)` |
| Скачать | `download_file(file_id)` — возвращает base64 |

Curl — fallback, когда MCP недоступен (например из shell-скрипта).

## Сохранение файлов

Для загрузки файла в filestorage2 — смотри `pandemonium-filestorage` → `workflow-dual-save.md`. Обязательные правила:
- Коллекция `pandemonium` — **всегда**
- Тег `pandemonium` — **всегда**
- Тег активной персоны (`$PANDEMONIUM_ACTIVE_PERSONA`, дефолт `bot-administrator`) — **всегда**

---

## Стратегии поиска

### 1. Полнотекстовый поиск

Основной инструмент — ищет по имени файла, описанию и содержимому (если индексировано).

```bash
curl -s "http://192.168.1.105:4733/api/files/search?q=<query>&limit=20&offset=0" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

Использовать когда: пользователь ищет по ключевым словам, теме, фрагменту названия.

### 2. Фильтрация по тегам

```bash
curl -s "http://192.168.1.105:4733/api/files?tag_ids=10,7&sort=created_at:desc" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

Использовать когда: пользователь ищет по конкретному тегу или комбинации тегов.

**Чтобы найти ID тега по имени:**

```bash
curl -s "http://192.168.1.105:4733/api/tags" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

### 3. Фильтрация по коллекции

```bash
curl -s "http://192.168.1.105:4733/api/collections/<id>/files" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

Использовать когда: пользователь ищет файлы в конкретной коллекции.

### 4. Фильтрация по типу файла

```bash
curl -s "http://192.168.1.105:4733/api/files?type=image&sort=created_at:desc" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

Доступные типы: `image`, `video`, `audio`, `document`, `archive`, `other`.

### 5. Комбинированная фильтрация

```bash
curl -s "http://192.168.1.105:4733/api/files?tag_ids=10&collection_ids=2&type=document&sort=created_at:desc" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

### 6. Метаданные конкретного файла

```bash
curl -s "http://192.168.1.105:4733/api/files/<id>" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

---

## Алгоритм поиска

```
1. Понять, что ищет пользователь:
   — Ключевые слова? → полнотекстовый поиск (#1)
   — Конкретный тег/домен? → фильтрация по тегам (#2)
   — Коллекция? → фильтрация по коллекции (#3)
   — Тип файла? → фильтрация по типу (#4)
   — Комбинация? → комбинированная фильтрация (#5)

2. Если поиск по тегу — сначала получить список тегов (GET /api/tags),
   найти нужный ID, затем фильтровать.

3. Если результатов много — показать список и уточнить у пользователя.

4. Если результатов нет — попробовать альтернативную стратегию:
   — Полнотекстовый не нашёл → попробовать по тегам
   — По тегам не нашёл → полнотекстовый с другими ключевыми словами

5. Когда файл найден — скачать и отправить с подписью.
```

---

## Скачивание файла

```bash
curl -s -o /tmp/<filename> "http://192.168.1.105:4733/api/files/<id>/download" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"
```

Имя файла брать из поля `original_filename` метаданных.

---

## Отправка файла пользователю

После скачивания — отправить через `$PANDEMONIUM_SEND_FILE` с подписью-метаданными.

### Формат подписи

```
📄 <title или original_filename>
Теги: #tag1 #tag2 #tag3
Коллекции: col1, col2
<description>

🗄 filestorage2 · id:<file_id>
```

**Правила формирования подписи:**

1. **Title** — поле `description` файла (в filestorage2 это играет роль title), или `original_filename` если описание пустое
2. **Теги** — все теги файла через `#`, получить из метаданных файла
3. **Коллекции** — все коллекции, в которых состоит файл
4. **Description** — поле `description`, если оно содержит больше чем одну строку (title)
5. **Footer** — идентификатор в filestorage2 для быстрого обращения к файлу в будущем
6. Подпись ≤ 1024 символов (лимит Telegram). Обрезать description если не помещается.

### Получение тегов и коллекций файла

Метаданные файла (`GET /api/files/<id>`) содержат теги и коллекции. Структура ответа:

```json
{
  "id": 42,
  "original_filename": "document.pdf",
  "description": "Описание файла",
  "mime_type": "application/pdf",
  "size": 123456,
  "tags": [
    {"id": 10, "name": "pandemonium", "color": "#f59e0b"},
    {"id": 7, "name": "skill/analytical-psychology", "color": "#8b5cf6"}
  ],
  "collections": [
    {"id": 2, "name": "pandemonium"}
  ],
  "created_at": "2026-04-03T11:35:00Z",
  "file_group_id": "550e8400-..."
}
```

### Bash-пример отправки

```bash
# Получить метаданные
META=$(curl -s "http://192.168.1.105:4733/api/files/42" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY")

FILENAME=$(echo "$META" | jq -r '.original_filename')
DESCRIPTION=$(echo "$META" | jq -r '.description // empty')
TITLE="${DESCRIPTION:-$FILENAME}"
TAGS=$(echo "$META" | jq -r '[.tags[].name] | map("#" + .) | join(" ")')
COLLECTIONS=$(echo "$META" | jq -r '[.collections[].name] | join(", ")')
FILE_ID=$(echo "$META" | jq -r '.id')

# Скачать
curl -s -o "/tmp/$FILENAME" "http://192.168.1.105:4733/api/files/42/download" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"

# Сформировать подпись
CAPTION="📄 $TITLE
Теги: $TAGS
Коллекции: $COLLECTIONS
🗄 filestorage2 · id:$FILE_ID"

# Отправить
$PANDEMONIUM_SEND_FILE "/tmp/$FILENAME" "$CAPTION"
```

---

## Множественные результаты

Если поиск вернул несколько файлов и пользователь не указал конкретный:

1. **Показать список** — номер, имя, теги, размер, дата.
2. **Спросить** — какой файл отправить (или все).
3. **Если пользователь просит все** — отправлять по одному с подписью каждого.

### Формат списка результатов

```
Найдено N файлов:

1. 📄 document.pdf — #skill/analytical-psychology #type/theory
   id:42 · 125 KB · 2026-04-03

2. 📄 notes.md — #skill/rational-emotive-therapy #type/note
   id:55 · 3 KB · 2026-04-04

Какой отправить? (номер или «все»)
```

---

## Известные ID

| Сущность | ID |
|----------|----|
| Коллекция `pandemonium` | 2 |
| Тег `pandemonium` | 10 |
| Тег `persona` | 9 |
| Тег `bot-administrator` | 11 |

---

## Ошибки

| Ситуация | Действие |
|----------|----------|
| filestorage2 недоступен (таймаут / connection refused) | Сообщить пользователю, что малинка недоступна |
| 401 Unauthorized | Проверить `$RASPBERY_FILESTORAGE_KEY` |
| 404 файл не найден | Файл был удалён, сообщить пользователю |
| Поиск не дал результатов | Попробовать альтернативную стратегию, сообщить если ничего не найдено |
| Файл слишком большой для Telegram (>50 MB) | Сообщить размер и предложить скачать другим способом |

Таймаут подключения: 5 секунд.

## See Also

- `filestorage2-api` — полный справочник API
- `pandemonium-filestorage` — локальное файловое хранилище
- `pandemonium-tagging-system.md` — система тегирования
