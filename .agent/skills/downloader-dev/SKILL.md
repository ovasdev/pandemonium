---
name: downloader-dev
description: "Development rules, stack, conventions for the Downloader Telegram bot project. Triggers when writing or reviewing code for the downloader."
---

# downloader-dev — Правила разработки

## Стек

- **Python** 3.12+, asyncio
- **aiogram** 3.x — Telegram Bot API
- **yt-dlp** — скачивание медиа (видео, аудио, субтитры)
- **beautifulsoup4** + **readability-lxml** — извлечение текста из статей
- **aiohttp** — HTTP-клиент (скачивание файлов, API вызовы к filestorage2)
- **pydantic** 2.x — валидация конфигурации и данных
- **PyYAML** — конфиг
- **uv** — пакетный менеджер
- **pytest** + **pytest-asyncio** — тесты

## Конвенции кода

- Python 3.12+ синтаксис: `type X = ...`, `match/case`, `X | Y` для union-типов
- Типизация обязательна для всех публичных функций
- `dataclass` или `pydantic.BaseModel` для структур данных
- `async/await` для всего I/O
- `logging` вместо `print()`
- Импорты: stdlib → third-party → local, разделённые пустой строкой

## Конфигурация

```yaml
# config.yaml
bot_token: "123456:ABC..."
allowed_users:
  - 12345678
marginalias:
  url: "https://marginalias.net"
  api_key: "sk-fs2-..."
download_dir: "/tmp/downloader"
media:
  preferred_audio_langs: ["ru", "uk", "en"]
  video_quality: "720p"  # умеренно хорошее
  download_subtitles: true
  subtitle_lang: "original"
```

## Структура модулей

```
src/downloader/
├── main.py                  # Точка входа (бот + CLI)
├── __main__.py              # python -m downloader
├── config.py                # Загрузка YAML + pydantic-валидация
├── bot/
│   ├── handlers.py          # URL → определение типа → dispatch
│   ├── middleware.py         # Whitelist авторизация
│   └── formatters.py        # Форматирование результата со ссылками
├── downloaders/
│   ├── base.py              # Protocol: async download(url) -> list[DownloadResult]
│   ├── media.py             # yt-dlp обёртка
│   ├── file.py              # aiohttp прямое скачивание
│   └── article.py           # readability + beautifulsoup
├── storage/
│   ├── base.py              # Protocol: async upload(file) -> StorageResult
│   ├── marginalias.py       # filestorage2 API клиент
│   └── local.py             # Сохранение в локальную FS
├── models.py                # DownloadResult, StorageResult, ContentType
└── cli.py                   # argparse CLI для standalone использования
```

## Модели данных

```python
from enum import StrEnum
from pydantic import BaseModel

class ContentType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLES = "subtitles"
    FILE = "file"
    ARTICLE = "article"

class DownloadResult(BaseModel):
    content_type: ContentType
    file_path: Path
    title: str
    description: str
    source_url: str
    mime_type: str | None = None

class StorageResult(BaseModel):
    url: str
    title: str
    description: str
    content_type: ContentType
```

## Паттерн обработки URL

```python
async def handle_url(url: str, config: Config) -> list[StorageResult]:
    content_type = detect_content_type(url)
    match content_type:
        case "media":
            downloader = MediaDownloader(config.media)
        case "article":
            downloader = ArticleDownloader()
        case _:
            downloader = FileDownloader()

    results = await downloader.download(url, config.download_dir)
    storage = MarginaliasStorage(config.marginalias)
    return [await storage.upload(r) for r in results]
```

## Обработка ошибок

- Собственные исключения: `DownloaderError`, `StorageError`, `UnsupportedURLError`
- Retry для сетевых ошибок (aiohttp, yt-dlp) — до 3 попыток с exponential backoff
- Таймауты: скачивание файла — 5 мин, видео — 30 мин, API вызовы — 30 сек
- Пользователю — понятное сообщение, не traceback

## Безопасность

- Валидация URL перед скачиванием (схема http/https, запрет локальных адресов)
- Санитизация имён файлов (убрать `../`, спецсимволы)
- Лимит размера скачиваемого файла (конфигурируется)
- Секреты только в конфиге, не в коде

## Тесты

- `pytest` + `pytest-asyncio`
- Файлы: `tests/test_{module}.py`
- Мокать внешние сервисы (yt-dlp, aiohttp, filestorage2 API)
- Запуск: `uv run pytest`

## Зависимости

```bash
uv add aiogram yt-dlp beautifulsoup4 readability-lxml aiohttp pydantic pyyaml
uv add --dev pytest pytest-asyncio
```
