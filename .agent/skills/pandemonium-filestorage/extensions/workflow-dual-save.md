---
title: "Dual Save: локальное хранилище + filestorage2 на Raspberry Pi"
skill: pandemonium-filestorage
type: workflow
domains:
  - программирование
  - администрирование
related:
  - filestorage2-api
created: 2026-04-03
---

# Dual Save Workflow

Когда пользователь просит **сохранить** файл — всегда выполняется двойное сохранение:

1. **Локально** — через `pandemonium.filestorage.FileStorage`
2. **Удалённо** — через filestorage2 REST API на Raspberry Pi

## Конфигурация filestorage2

| Параметр | Значение |
|----------|---------|
| BASE_URL | `http://192.168.1.105:4733` |
| API_KEY  | `$RASPBERY_FILESTORAGE_KEY` (env) |
| Обязательная коллекция | `pandemonium` (id: 2) |
| Обязательный тег | `pandemonium` + slug активной персоны (`$PANDEMONIUM_ACTIVE_PERSONA`, дефолт `bot-administrator`) |

## Клиент: MCP или curl

Предпочитай MCP — сервер `filestorage2` зарегистрирован в user-scope Claude Code, инструменты вида `mcp__filestorage2__*`:

| Операция | MCP tool | Curl fallback |
|----------|----------|---------------|
| Загрузка | `upload_file(filename, content_base64, title, description)` | `POST /api/files` (multipart) |
| Список тегов | `list_tags` | `GET /api/tags` |
| Создать тег | `create_tag(name, color)` | `POST /api/tags` |
| Повесить теги | `attach_tags(file_group_id, tag_uuids)` | `POST /api/files/{fgid}/tags` |
| Список коллекций | `list_collections` | `GET /api/collections` |
| Добавить в коллекцию | `add_files_to_collection(collection_id, file_group_ids)` | `POST /api/collections/{id}/files` |
| Поиск | `search_files(q)` / `list_files(filters)` | `GET /api/files/search` / `GET /api/files` |

MCP работает с UUID (`file_group_id`, `tag.uuid`, `collection.uuid`). curl может использовать числовой `id` для эндпоинтов первого класса, но для связочных — тоже UUID.

## Шаги

### 1. Подготовить метаданные

Определить теги и коллекции по системе тегирования (`pandemonium-tagging-system.md`):

- **Pandemonium tag** — `pandemonium` (обязателен)
- **Persona tag** — slug активной персоны (`$PANDEMONIUM_ACTIVE_PERSONA`, дефолт `bot-administrator`) — **обязателен**
- **Skill tag** — к какому скилу относится файл (e.g. `analytical-psychology`)
- **Type tag** — тип документа (e.g. `workflow`, `reference`, `theory`)
- **Domain tags** — смысловые области (e.g. `психология`, `программирование`)
- **Коллекции** — `pandemonium` (обязательная) + дополнительные по контексту

### 2. Сохранить локально

```python
from pandemonium.filestorage import FileStorage, FileMeta
from pathlib import Path

fs = FileStorage(Path("./collections"))
meta = FileMeta(
    title="...",
    tags=["skill/...", "type/...", "domain/..."],
    collections=["pandemonium", ...],
    description="...",
)
entries = fs.save(source_path, filename, meta)
```

### 3. Загрузить в filestorage2 (MCP)

```
upload_file(
  filename="display-name.ext",
  content_base64=<base64(file_bytes)>,
  title="...",
  description="...",
)
# → file object: { id, file_group_id, ... }
```

Запомнить `file_group_id` (UUID) — он нужен всем последующим операциям.

**Curl fallback:**
```bash
FGID=$(curl -s -X POST "http://192.168.1.105:4733/api/files" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY" \
  -F "file=@/path/to/file;filename=display-name.ext" \
  -F "description=..." | jq -r '.file_group_id')
```

### 4. Добавить в коллекцию pandemonium — ОБЯЗАТЕЛЬНО

Получить UUID коллекции `pandemonium` (один раз на сессию):

```
list_collections  # найти { name: "pandemonium" } → collection.uuid
add_files_to_collection(collection_id=<pandemonium_uuid>, file_group_ids=[<fgid>])
```

**Curl fallback** (через числовой id=2):
```bash
curl -s -X POST "http://192.168.1.105:4733/api/collections/<pandemonium-uuid>/files" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"file_group_ids\": [\"$FGID\"]}"
```

### 5. Присвоить теги — ОБЯЗАТЕЛЬНО `pandemonium` + тег персоны

Получить список тегов (один раз на сессию), найти нужные UUID. Отсутствующие — создать.

```
list_tags
# Для каждого тега, которого нет в ответе:
create_tag(name="<имя>", color="<hex>")

attach_tags(
  file_group_id=<fgid>,
  tag_uuids=[
    <uuid of "pandemonium">,        # ВСЕГДА
    <uuid of "$PANDEMONIUM_ACTIVE_PERSONA">,  # ВСЕГДА (например "bot-administrator")
    <uuid of "skill/...">,          # по контексту
    <uuid of "type/...">,
    <uuid of "domain/...">,
  ],
)
```

**Два мандатных тега:** `pandemonium` + slug активной персоны. Без них сохранение считается некорректным.

**Curl fallback:**
```bash
curl -s -X POST "http://192.168.1.105:4733/api/files/$FGID/tags" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tag_uuids": ["<uuid1>", "<uuid2>", ...]}'
```

### 6. Добавить в дополнительные коллекции (если нужно)

Если файл относится к другим коллекциям помимо `pandemonium` — добавить через `add_files_to_collection`. Создать коллекцию (`create_collection`), если не существует.

### 7. Отправить в Telegram (если в контексте бота)

Если установлены `PANDEMONIUM_SEND_FILE` и `PANDEMONIUM_CHAT_ID` — отправить **сам сохранённый файл** с caption, содержащим title, теги, коллекции и description (см. основной SKILL.md, секция "Workflow: Telegram-контекст").

## Цвета тегов (конвенция)

| Категория | Цвет | Пример |
|-----------|------|--------|
| skill/* | `#8b5cf6` (фиолетовый) | skill/analytical-psychology |
| type/* | `#3b82f6` (синий) | type/workflow |
| domain/* | `#10b981` (зелёный) | domain/психология |
| pandemonium | `#f59e0b` (жёлтый) | pandemonium |

## Известные ID

| Сущность | ID | Тип |
|----------|----|-----|
| Коллекция `pandemonium` | 2 | collection |
| Тег `pandemonium` | 10 | tag |
| Тег `persona` | 9 | tag |
| Тег `bot-administrator` | 11 | tag |

## Ошибки

- Если filestorage2 недоступен — сохранить локально, сообщить пользователю об ошибке удалённого сохранения
- Если локальное сохранение не удалось — не загружать на filestorage2, сообщить об ошибке
- Таймаут подключения: 5 секунд
