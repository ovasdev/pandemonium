---
name: pandemonium-filestorage
description: "Reference for pandemonium.filestorage — local collections-based file storage library. Triggers when working with FileStorage API, saving/listing/searching files in collections, parsing file captions with metadata (tags, collections, title, description). Also applies when building agent tools that interact with file storage."
---

# pandemonium.filestorage — Локальное файловое хранилище

Библиотека для работы с коллекциями файлов. Файлы хранятся в директориях-коллекциях с YAML-frontmatter метаданными. Не требует сервера — работает с файловой системой напрямую.

## Когда использовать

- Сохранение файлов в коллекции с тегами и метаданными
- Поиск, листинг, фильтрация файлов по коллекциям и тегам
- Построение agent tools поверх файлового хранилища
- Интеграция с Telegram-ботом (загрузка файлов от пользователя)

## Когда НЕ использовать

- Работа с удалённым filestorage2 сервером → скил `filestorage2-api`
- Работа с протоколами сессий бота → `ProtocolStorage` в `tgbot/storage/`

## Расположение

```
src/pandemonium/filestorage/
├── __init__.py    — публичный экспорт
├── models.py      — FileMeta, FileEntry, CollectionInfo
├── parser.py      — parse_caption()
└── storage.py     — FileStorage (основной класс)
```

## Импорт

```python
from pandemonium.filestorage import FileStorage, parse_caption, FileMeta, FileEntry, CollectionInfo
```

## Модели

### FileMeta

Входные метаданные для сохранения файла.

```python
@dataclass
class FileMeta:
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    description: str = ""
```

### FileEntry

Файл, существующий в хранилище. Возвращается всеми read-операциями.

```python
@dataclass
class FileEntry:
    path: str              # относительный путь от base (e.g. "наука/doc.md")
    original_filename: str
    title: str
    tags: list[str]
    collections: list[str]
    description: str
    added: str             # "2026-04-03 11:35 UTC"

    @property
    def collection(self) -> str:  # первая директория в path
```

### CollectionInfo

```python
@dataclass
class CollectionInfo:
    name: str        # имя директории
    slug: str        # slug (= name)
    file_count: int  # количество файлов (без .meta.md)
```

## API — FileStorage

### Инициализация

```python
fs = FileStorage(base_path=Path("/path/to/collections"))
```

`base_path` — корневая директория коллекций. Создаётся автоматически.

### save(source, original_filename, meta) → list[FileEntry]

Сохраняет файл в хранилище. Возвращает список созданных записей (по одной на коллекцию).

```python
meta = FileMeta(
    title="Основы метафизики",
    tags=["философия", "кант"],
    collections=["наука", "философия"],
    description="Трактат Канта по этике",
)
entries = fs.save(Path("/tmp/book.md"), "book.md", meta)
```

**Правила сохранения:**
- `.md` файлы — frontmatter инжектится в сам файл
- Другие файлы — копируются + создаётся sidecar `<filename>.meta.md`
- Если `collections` пуст — сохраняется в `uncategorized/`
- Несколько коллекций — файл копируется в каждую
- Коллизии имён — автоматический суффикс `-1`, `-2`, ...
- Директории коллекций создаются автоматически

### list_collections() → list[CollectionInfo]

```python
for col in fs.list_collections():
    print(f"{col.name}: {col.file_count} files")
```

### list_files(collection?, tag?) → list[FileEntry]

```python
# Все файлы
all_files = fs.list_files()

# Файлы в коллекции
science = fs.list_files(collection="наука")

# Файлы с тегом
tagged = fs.list_files(tag="философия")

# Комбинация
filtered = fs.list_files(collection="наука", tag="кант")
```

### get_file(relative_path) → FileEntry | None

```python
entry = fs.get_file("наука/основы-метафизики.md")
if entry:
    print(entry.title, entry.tags)
```

### search(query) → list[FileEntry]

Поиск подстрокой (case-insensitive) по title, tags, description.

```python
results = fs.search("метафизика")
```

### delete_file(relative_path) → bool

Удаляет файл и его sidecar (если есть).

```python
fs.delete_file("uncategorized/old-file.pdf")
```

## Парсер caption

```python
from pandemonium.filestorage import parse_caption

meta = parse_caption("""title: Основы метафизики нравственности
collections: психология, мистика
#философия #кант
Очень важная книга по этике Канта""")

# meta.title       → "Основы метафизики нравственности"
# meta.collections → ["психология", "мистика"]
# meta.tags        → ["философия", "кант"]
# meta.description → "Очень важная книга по этике Канта"
```

**Формат caption:**
- `title: <значение>` — заголовок (одна строка)
- `collections: <col1>, <col2>` — коллекции через запятую (одна строка)
- `#тег1 #тег2` — теги в любом месте текста
- Всё остальное — description

Порядок директив не важен. Директивы case-insensitive.

## Структура хранилища на диске

```
collections/
├── наука/
│   ├── основы-метафизики.md          # markdown с frontmatter
│   └── article.pdf                    # бинарный файл
│       article.pdf.meta.md            # sidecar с метаданными
├── философия/
│   └── основы-метафизики.md          # копия (если в нескольких коллекциях)
└── uncategorized/
    └── random-file.txt
        random-file.txt.meta.md
```

### Frontmatter (markdown файлы)

```yaml
---
title: Основы метафизики нравственности
tags:
  - философия
  - кант
collections:
  - наука
  - философия
description: Очень важная книга по этике Канта
original_file: book.md
added: 2026-04-03 11:35 UTC
---
```

### Sidecar (бинарные файлы)

Файл `photo.jpg.meta.md`:

```yaml
---
title: Фотография
tags:
  - фото
collections:
  - архив
description: Описание фотографии
original_file: photo.jpg
added: 2026-04-03 11:35 UTC
---

# photo.jpg

Описание фотографии
```

## Интеграция с ботом

Бот использует `FileStorage` в обработчике документов (`handlers.py`):

```python
from pandemonium.filestorage import FileStorage, parse_caption

# В handle_document_message:
meta = parse_caption(caption)
storage = FileStorage(config.storage.collections_path)
entries = storage.save(source=tmp_path, original_filename=name, meta=meta)
```

Конфиг: `StorageConfig.collections_path` (дефолт: `collections/` в корне проекта).

## Workflow: Telegram-контекст

Если операция с filestorage происходит в контексте Pandemonium бота (установлены `PANDEMONIUM_SEND_FILE`, `PANDEMONIUM_CHAT_ID`), после сохранения файла **отправь сам сохранённый файл** в Telegram с описательным caption.

### Когда отправлять

- После `fs.save()` вызванного агентом (не из обработчика бота — бот сам формирует ответ)
- После `tool_save_file()` если работаешь как agent tool

### Формат caption

Caption содержит метаданные файла — title, теги, коллекции, description:

```
📄 <title>
Теги: #tag1 #tag2
Коллекции: col1, col2
<description>
```

**Порядок полей**: title → теги → коллекции → description.
Поле `Путь:` не включается — пользователю важны метаданные, а не внутренний путь.

### Bash-пример

```bash
$PANDEMONIUM_SEND_FILE /abs/path/to/saved/file.md "📄 Основы метафизики нравственности
Теги: #философия #кант
Коллекции: наука, философия
Трактат Канта по этике"
```

### Python-пример

```python
import os
import subprocess
from pathlib import Path

def send_saved_file(entry: FileEntry, base_path: Path) -> None:
    """Send the saved file to Telegram with metadata caption."""
    send_file = os.environ.get("PANDEMONIUM_SEND_FILE")
    if not send_file:
        return

    abs_path = base_path / entry.path
    tags_str = " ".join(f"#{t}" for t in entry.tags) if entry.tags else "—"
    cols_str = ", ".join(entry.collections) if entry.collections else "—"

    lines = [f"📄 {entry.title}"]
    lines.append(f"Теги: {tags_str}")
    lines.append(f"Коллекции: {cols_str}")
    if entry.description:
        lines.append(entry.description)

    caption = "\n".join(lines)
    subprocess.run([send_file, str(abs_path), caption], check=False)
```

### Правила

- Отправляется **сам сохранённый файл** из первой коллекции (первый entry) с caption
- Если `$PANDEMONIUM_SEND_FILE` не задан — вывести метаданные текстом в ответ
- Caption ограничен 1024 символами (лимит Telegram) — обрезай description если нужно
- Когда на сервере появится сущность **artifact** — добавить поле `Артефакт:` в caption после title

## Построение agent tool

Пример обёртки для использования как tool:

```python
from pathlib import Path
from pandemonium.filestorage import FileStorage, FileMeta

fs = FileStorage(Path("./collections"))

def tool_save_file(file_path: str, title: str = "", tags: str = "", collections: str = "", description: str = "") -> str:
    meta = FileMeta(
        title=title or None,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        collections=[c.strip() for c in collections.split(",") if c.strip()],
        description=description,
    )
    entries = fs.save(Path(file_path), Path(file_path).name, meta)
    return f"Saved to: {', '.join(e.path for e in entries)}"

def tool_search_files(query: str) -> str:
    results = fs.search(query)
    if not results:
        return "No files found."
    return "\n".join(f"- {e.path}: {e.title} [{', '.join(e.tags)}]" for e in results)

def tool_list_collections() -> str:
    cols = fs.list_collections()
    if not cols:
        return "No collections."
    return "\n".join(f"- {c.name}: {c.file_count} files" for c in cols)

def tool_list_files(collection: str = "", tag: str = "") -> str:
    results = fs.list_files(
        collection=collection or None,
        tag=tag or None,
    )
    if not results:
        return "No files found."
    return "\n".join(f"- {e.path}: {e.title}" for e in results)

def tool_delete_file(path: str) -> str:
    ok = fs.delete_file(path)
    return "Deleted." if ok else "File not found."
```

## Ограничения

- Синхронный API (файловые операции) — для async обёртывать в `asyncio.to_thread`
- Поиск — линейный перебор, не индекс (достаточно для тысяч файлов)
- Несколько коллекций = несколько копий файла (не symlink)
- Нет блокировок — не для конкурентной записи из нескольких процессов
