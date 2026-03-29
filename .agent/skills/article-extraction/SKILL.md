---
name: article-extraction
description: "Patterns for downloading web pages and extracting meaningful article text using readability-lxml and BeautifulSoup. Triggers when working with article/webpage content extraction, text cleanup, or HTML parsing."
---

# article-extraction — Извлечение текста из статей

## Обзор

Алгоритмическое извлечение значимого текста из веб-страниц. Убирает навигацию, рекламу, сайдбары — оставляет основной контент.

## Стек

- **readability-lxml** — порт Mozilla Readability, определяет основной контент страницы
- **beautifulsoup4** + **lxml** — парсинг и очистка HTML
- **aiohttp** — асинхронное скачивание страниц

## Установка

```bash
uv add readability-lxml beautifulsoup4 lxml aiohttp
```

## Базовый пайплайн

```python
import aiohttp
from readability import Document
from bs4 import BeautifulSoup

async def extract_article(url: str) -> ArticleResult:
    # 1. Скачиваем страницу
    html = await fetch_page(url)

    # 2. Извлекаем основной контент через readability
    doc = Document(html)
    title = doc.title()
    content_html = doc.summary()

    # 3. Очищаем HTML → чистый текст
    text = html_to_text(content_html)

    return ArticleResult(
        title=title,
        text=text,
        source_url=url,
    )
```

## Скачивание страницы

```python
async def fetch_page(url: str, timeout: int = 30) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Downloader/1.0)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ru,en;q=0.9",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            resp.raise_for_status()
            return await resp.text()
```

## Извлечение контента (readability)

```python
from readability import Document

def extract_content(html: str) -> tuple[str, str]:
    """Возвращает (title, content_html)."""
    doc = Document(html)
    return doc.title(), doc.summary()
```

### Как работает readability

1. Парсит HTML в DOM-дерево
2. Оценивает каждый блок по эвристикам (длина текста, соотношение текст/ссылки, теги)
3. Выбирает блок с наивысшим score как основной контент
4. Убирает навигацию, сайдбары, рекламу, комментарии
5. Возвращает очищенный HTML основного контента

## Очистка HTML → текст

```python
from bs4 import BeautifulSoup
import re

def html_to_text(html: str) -> str:
    """Конвертирует HTML в чистый текст с сохранением структуры."""
    soup = BeautifulSoup(html, "lxml")

    # Убираем скрипты и стили
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Заменяем блочные теги на переносы строк
    for tag in soup.find_all(["p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = soup.get_text()

    # Нормализация пробелов
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
```

## Сохранение в Markdown

```python
def article_to_markdown(title: str, text: str, source_url: str) -> str:
    """Форматирует статью как Markdown."""
    return f"# {title}\n\n> Источник: {source_url}\n\n{text}\n"
```

## Сохранение в файл

```python
from pathlib import Path
import re

def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Безопасное имя файла из заголовка."""
    name = re.sub(r'[<>:"/\\|?*]', '', title)
    name = name.strip('. ')
    return name[:max_length] or "untitled"

async def save_article(url: str, output_dir: str) -> Path:
    result = await extract_article(url)
    filename = sanitize_filename(result.title) + ".md"
    path = Path(output_dir) / filename
    path.write_text(
        article_to_markdown(result.title, result.text, url),
        encoding="utf-8",
    )
    return path
```

## Определение: это статья или нет?

```python
from urllib.parse import urlparse

# Домены, которые yt-dlp обработает лучше
MEDIA_DOMAINS = {
    "youtube.com", "youtu.be", "facebook.com", "fb.watch",
    "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "vimeo.com", "dailymotion.com",
}

def looks_like_article(url: str) -> bool:
    """Эвристика: URL похож на статью, а не на медиа."""
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    if domain in MEDIA_DOMAINS:
        return False
    # Прямые ссылки на файлы
    path = urlparse(url).path.lower()
    if any(path.endswith(ext) for ext in [".mp4", ".mp3", ".pdf", ".zip", ".rar"]):
        return False
    return True
```

## Обработка ошибок

```python
class ArticleExtractionError(Exception):
    pass

async def safe_extract(url: str) -> ArticleResult | None:
    try:
        html = await fetch_page(url)
    except aiohttp.ClientError as e:
        raise ArticleExtractionError(f"Не удалось скачать страницу: {e}")

    doc = Document(html)
    text = html_to_text(doc.summary())

    # Если текст слишком короткий — readability не нашёл контент
    if len(text.strip()) < 100:
        raise ArticleExtractionError("Не удалось извлечь текст статьи")

    return ArticleResult(
        title=doc.title(),
        text=text,
        source_url=url,
    )
```

## Ограничения

- **JS-rendered страницы**: readability работает с HTML. SPA-сайты могут вернуть пустой контент. Для них нужен playwright/selenium (пока не поддерживается)
- **Paywalled контент**: скачает только то, что доступно без авторизации
- **PDF-статьи**: это не HTML — обрабатывать отдельно (как файл)
- **Кодировка**: aiohttp обычно определяет автоматически, но бывают edge cases с windows-1251
