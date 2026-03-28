"""Tests for file receiving handlers (document and photo)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pandemonium.tgbot.bot.handlers import _download_file, handle_document_message, handle_photo_message
from pandemonium.tgbot.config import StorageConfig


# ── StorageConfig.uploads_path ──────────────────────────────────────────


def test_uploads_path(tmp_path):
    cfg = StorageConfig(base_path=tmp_path)
    assert cfg.uploads_path == tmp_path / "uploads"


# ── _download_file ──────────────────────────────────────────────────────


async def test_download_file(tmp_path):
    bot = AsyncMock()
    tg_file = MagicMock()
    tg_file.file_path = "documents/file_123.pdf"
    bot.get_file.return_value = tg_file
    bot.download_file = AsyncMock()

    dest = tmp_path / "uploads"
    result = await _download_file(bot, "file_id_abc", dest)

    assert dest.exists()
    assert result == dest / "file_id_abc.pdf"
    bot.get_file.assert_awaited_once_with("file_id_abc")
    bot.download_file.assert_awaited_once_with("documents/file_123.pdf", destination=result)


async def test_download_file_no_extension(tmp_path):
    bot = AsyncMock()
    tg_file = MagicMock()
    tg_file.file_path = "photos/file_456"
    bot.get_file.return_value = tg_file
    bot.download_file = AsyncMock()

    dest = tmp_path / "uploads"
    result = await _download_file(bot, "file_id_xyz", dest)

    assert result == dest / "file_id_xyz"


# ── handle_document_message ─────────────────────────────────────────────


def _make_message(chat_id: int = 100, user_id: int = 42, message_id: int = 1):
    msg = AsyncMock()
    msg.chat.id = chat_id
    msg.chat.type = "private"
    msg.from_user.id = user_id
    msg.message_id = message_id
    msg.reply = AsyncMock()
    return msg


def _make_config(tmp_path: Path):
    config = MagicMock()
    config.storage.uploads_path = tmp_path / "uploads"
    config.default_project.id = "proj"
    config.default_project.name = "Test"
    config.default_project.path = tmp_path
    return config


def _make_session_manager(active: bool = False):
    sm = AsyncMock()
    if active:
        session = MagicMock()
        session.state = MagicMock()
        session.state.__eq__ = lambda self, other: True  # matches RUNNING
        sm.active_session = session
    else:
        sm.active_session = None
    sm.create_request = AsyncMock(return_value=1)
    return sm


async def test_handle_document_rejects_when_busy(tmp_path):
    msg = _make_message()
    config = _make_config(tmp_path)
    sm = MagicMock()
    active = MagicMock()

    from pandemonium.tgbot.session.state import SessionState
    active.state = SessionState.RUNNING
    sm.active_session = active

    await handle_document_message(msg, AsyncMock(), config, sm, bot_username="testbot")
    msg.reply.assert_awaited_once()
    assert "already in progress" in msg.reply.call_args[0][0]


async def test_handle_document_downloads_and_creates_request(tmp_path):
    msg = _make_message()
    doc = MagicMock()
    doc.file_name = "report.pdf"
    doc.file_id = "tg_file_id_1"
    doc.file_unique_id = "uniq1"
    msg.document = doc
    msg.caption = "Проанализируй этот файл"
    msg.photo = None

    config = _make_config(tmp_path)

    sm = MagicMock()
    sm.active_session = None
    sm.create_request = AsyncMock(return_value=1)

    status_msg = AsyncMock()
    status_msg.message_id = 99
    msg.reply = AsyncMock(return_value=status_msg)

    # After create_request, active_session returns a session
    post_session = MagicMock()
    post_session.request_id = 10
    sm.active_session = post_session

    bot = AsyncMock()
    tg_file = MagicMock()
    tg_file.file_path = "documents/file_1.pdf"
    bot.get_file.return_value = tg_file
    bot.download_file = AsyncMock()

    # Create the uploads dir and the downloaded file so rename works
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "tg_file_id_1.pdf").touch()

    await handle_document_message(msg, bot, config, sm, bot_username="testbot")

    sm.create_request.assert_awaited_once()
    call_kwargs = sm.create_request.call_args[1]
    assert "report.pdf" in call_kwargs["prompt"]
    assert "Проанализируй этот файл" in call_kwargs["prompt"]


async def test_handle_document_no_caption(tmp_path):
    msg = _make_message()
    doc = MagicMock()
    doc.file_name = "data.csv"
    doc.file_id = "tg_file_id_2"
    doc.file_unique_id = "uniq2"
    msg.document = doc
    msg.caption = None
    msg.photo = None

    config = _make_config(tmp_path)

    sm = MagicMock()
    sm.active_session = None
    sm.create_request = AsyncMock(return_value=1)

    status_msg = AsyncMock()
    status_msg.message_id = 99
    msg.reply = AsyncMock(return_value=status_msg)

    post_session = MagicMock()
    post_session.request_id = 10
    sm.active_session = post_session

    bot = AsyncMock()
    tg_file = MagicMock()
    tg_file.file_path = "documents/file_2.csv"
    bot.get_file.return_value = tg_file
    bot.download_file = AsyncMock()

    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "tg_file_id_2.csv").touch()

    await handle_document_message(msg, bot, config, sm, bot_username="testbot")

    call_kwargs = sm.create_request.call_args[1]
    assert "data.csv" in call_kwargs["prompt"]
    assert "User message:" not in call_kwargs["prompt"]


# ── handle_photo_message ────────────────────────────────────────────────


async def test_handle_photo_downloads_largest(tmp_path):
    msg = _make_message()
    small_photo = MagicMock()
    small_photo.file_id = "photo_small"
    large_photo = MagicMock()
    large_photo.file_id = "photo_large"
    msg.photo = [small_photo, large_photo]
    msg.caption = "Что на этом скриншоте?"
    msg.document = None

    config = _make_config(tmp_path)

    sm = MagicMock()
    sm.active_session = None
    sm.create_request = AsyncMock(return_value=1)

    status_msg = AsyncMock()
    status_msg.message_id = 99
    msg.reply = AsyncMock(return_value=status_msg)

    post_session = MagicMock()
    post_session.request_id = 10
    sm.active_session = post_session

    bot = AsyncMock()
    tg_file = MagicMock()
    tg_file.file_path = "photos/file_99.jpg"
    bot.get_file.return_value = tg_file
    bot.download_file = AsyncMock()

    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)

    await handle_photo_message(msg, bot, config, sm, bot_username="testbot")

    # Should use the last (largest) photo
    bot.get_file.assert_awaited_once_with("photo_large")
    sm.create_request.assert_awaited_once()
    call_kwargs = sm.create_request.call_args[1]
    assert "photo" in call_kwargs["prompt"].lower()
    assert "Что на этом скриншоте?" in call_kwargs["prompt"]
