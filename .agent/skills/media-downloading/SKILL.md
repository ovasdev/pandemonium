---
name: media-downloading
description: "Patterns for downloading video, audio, and subtitles from YouTube, Facebook, Instagram, X and other platforms using yt-dlp. Triggers when working with media downloads, yt-dlp configuration, or video/audio extraction."
---

# media-downloading — Скачивание медиа через yt-dlp

## Обзор

yt-dlp — форк youtube-dl, основной инструмент для скачивания медиа. Поддерживает 1000+ сайтов: YouTube, Facebook, Instagram, X (Twitter), TikTok, Vimeo и др.

## Установка

```bash
uv add yt-dlp
```

## Базовое использование (Python API)

```python
import yt_dlp

def download_video(url: str, output_dir: str) -> dict:
    opts = {
        "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info
```

## Скачивание видео (умеренное качество)

```python
VIDEO_OPTS = {
    # 720p — баланс качества и размера
    "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "merge_output_format": "mp4",
    "outtmpl": "%(title)s.%(ext)s",
    # Метаданные
    "writethumbnail": False,
    "writeinfojson": False,
}
```

## Скачивание аудиодорожки с приоритетом языка

```python
AUDIO_OPTS = {
    "format": "bestaudio/best",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
    "outtmpl": "%(title)s.%(ext)s",
}

def get_audio_opts_with_lang(preferred_langs: list[str]) -> dict:
    """
    preferred_langs: ["ru", "uk", "en"] — приоритет языков.
    Для YouTube: аудиодорожки разных языков доступны через format selection.
    """
    # Построение format string с приоритетом языка
    lang_formats = [f"bestaudio[language={lang}]" for lang in preferred_langs]
    lang_formats.append("bestaudio/best")
    return {
        **AUDIO_OPTS,
        "format": "/".join(lang_formats),
    }
```

## Скачивание субтитров

```python
SUBTITLE_OPTS = {
    "writesubtitles": True,
    "writeautomaticsub": True,  # Авто-сабы если нет ручных
    "subtitlesformat": "srt",
    "skip_download": True,  # Только субтитры, без видео
    "outtmpl": "%(title)s.%(ext)s",
}

def get_subtitle_opts_original_lang() -> dict:
    """Скачивает субтитры на языке оригинала."""
    return {
        **SUBTITLE_OPTS,
        # yt-dlp автоматически определяет язык оригинала
        # если subtitleslangs не указан — берёт все доступные
        # для оригинала: сначала extract_info, потом выбрать
    }
```

### Определение языка оригинала

```python
async def get_original_subtitle_lang(url: str) -> str | None:
    """Извлекает язык оригинала из метаданных видео."""
    opts = {"skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # Язык оригинала
        original_lang = info.get("language")
        # Доступные субтитры
        subtitles = info.get("subtitles", {})
        auto_subs = info.get("automatic_captions", {})

        if original_lang and original_lang in subtitles:
            return original_lang
        if original_lang and original_lang in auto_subs:
            return original_lang
        # Первый доступный
        if subtitles:
            return next(iter(subtitles))
        if auto_subs:
            return next(iter(auto_subs))
        return None
```

## Полный пайплайн: видео + аудио + субтитры

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class MediaResult:
    video_path: Path | None
    audio_path: Path | None
    subtitle_path: Path | None
    title: str
    description: str

async def download_media(url: str, output_dir: str, preferred_langs: list[str]) -> MediaResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # 1. Получаем метаданные
    with yt_dlp.YoutubeDL({"skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "untitled")
    description = info.get("description", "")

    # 2. Скачиваем видео
    video_opts = {
        **VIDEO_OPTS,
        "outtmpl": str(output / "%(title)s.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(video_opts) as ydl:
        ydl.download([url])

    # 3. Скачиваем аудио (с приоритетом языка)
    audio_opts = {
        **get_audio_opts_with_lang(preferred_langs),
        "outtmpl": str(output / "%(title)s_audio.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(audio_opts) as ydl:
        ydl.download([url])

    # 4. Субтитры на языке оригинала
    orig_lang = await get_original_subtitle_lang(url)
    if orig_lang:
        sub_opts = {
            **SUBTITLE_OPTS,
            "subtitleslangs": [orig_lang],
            "outtmpl": str(output / "%(title)s.%(ext)s"),
        }
        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.download([url])

    return MediaResult(
        video_path=...,  # resolve actual path
        audio_path=...,
        subtitle_path=...,
        title=title,
        description=description,
    )
```

## Определение поддерживаемых URL

```python
def is_supported_media_url(url: str) -> bool:
    """Проверяет, поддерживается ли URL для медиа-скачивания."""
    extractors = yt_dlp.extractor.gen_extractors()
    for extractor in extractors:
        if extractor.suitable(url):
            return extractor.IE_NAME != "generic"
    return False
```

## Обработка ошибок

```python
import yt_dlp

try:
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
except yt_dlp.utils.DownloadError as e:
    # Видео удалено, геоблокировка, возрастные ограничения
    logger.error("Download failed: %s", e)
except yt_dlp.utils.ExtractorError as e:
    # Проблемы с парсингом страницы
    logger.error("Extraction failed: %s", e)
```

## Ограничения и советы

- **Размер**: 720p видео ~500MB/час. Telegram лимит 50MB — для крупных файлов сохранять на marginalias
- **Rate limits**: YouTube может блокировать при частых запросах. Добавить `sleep_interval: 3`
- **Cookies**: для приватных видео — `cookiefile` в opts
- **Async**: yt-dlp синхронный — оборачивать в `asyncio.to_thread()`
