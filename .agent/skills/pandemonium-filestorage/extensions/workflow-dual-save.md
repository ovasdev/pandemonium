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

## Шаги

### 1. Подготовить метаданные

Определить теги и коллекции по системе тегирования (`pandemonium-tagging-system.md`):

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

### 3. Загрузить в filestorage2

```bash
# Upload file
FILE_ID=$(curl -s -X POST "http://192.168.1.105:4733/api/files" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY" \
  -F "file=@/path/to/file;filename=display-name.ext" \
  -F "description=..." | jq -r '.id')

# Add to pandemonium collection (id: 2) — ОБЯЗАТЕЛЬНО
curl -s -X POST "http://192.168.1.105:4733/api/collections/2/files" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"file_ids\": [$FILE_ID]}"
```

### 4. Присвоить теги

Перед присвоением тега — проверить, существует ли он. Если нет — создать.

```bash
# Получить существующие теги
curl -s "http://192.168.1.105:4733/api/tags" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY"

# Создать тег если не существует
curl -s -X POST "http://192.168.1.105:4733/api/tags" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "skill/analytical-psychology", "color": "#8b5cf6"}'

# Присвоить теги файлу
curl -s -X POST "http://192.168.1.105:4733/api/files/$FILE_ID/tags" \
  -H "Authorization: Bearer $RASPBERY_FILESTORAGE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": [10, ...]}'
```

**Тег `pandemonium` (id: 10) — всегда добавлять.**

### 5. Добавить в дополнительные коллекции (если нужно)

Если файл относится к другим коллекциям помимо `pandemonium` — добавить. Создать коллекцию, если не существует.

### 6. Отправить в Telegram (если в контексте бота)

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
