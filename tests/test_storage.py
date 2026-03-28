"""Tests for ProtocolStorage — filesystem protocol logging."""

import json

import pytest

from pandemonium.tgbot.storage.protocol import ProtocolStorage


@pytest.fixture
def storage(tmp_path):
    return ProtocolStorage(tmp_path)


def test_next_request_number_empty(storage):
    assert storage.next_request_number("proj") == 1


def test_next_request_number_increments(tmp_path):
    s = ProtocolStorage(tmp_path)
    (tmp_path / "proj" / "request_1").mkdir(parents=True)
    (tmp_path / "proj" / "request_3").mkdir(parents=True)
    assert s.next_request_number("proj") == 4


def test_next_request_number_ignores_non_dirs(tmp_path):
    s = ProtocolStorage(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "request_1").mkdir()
    (proj / "other_file.txt").write_text("ignore me")
    assert s.next_request_number("proj") == 2


async def test_save_request(storage, tmp_path):
    path = await storage.save_request("proj", 1, "Do something")
    assert path.exists()
    assert path.read_text() == "Do something"
    assert path.name == "request.md"
    assert path.parent.name == "request_1"


async def test_save_interaction_question(storage):
    path = await storage.save_interaction("proj", 1, 1, "What file?", is_response=False)
    assert path.name == "1.1.md"
    assert path.read_text() == "What file?"


async def test_save_interaction_response(storage):
    path = await storage.save_interaction("proj", 1, 1, "src/main.py", is_response=True)
    assert path.name == "1.1.response.md"
    assert path.read_text() == "src/main.py"


async def test_append_stream_log(storage, tmp_path):
    await storage.append_stream_log("proj", 1, "chunk1\n")
    await storage.append_stream_log("proj", 1, "chunk2\n")
    log_path = tmp_path / "proj" / "request_1" / "stream_log.md"
    assert log_path.read_text() == "chunk1\nchunk2\n"


async def test_save_report(storage):
    path = await storage.save_report("proj", 1, "# Report\nAll done.")
    assert path.name == "report.md"
    assert "All done." in path.read_text()


async def test_save_error(storage):
    path = await storage.save_error("proj", 1, "Process crashed")
    assert path.name == "error.md"
    assert path.read_text() == "Process crashed"


async def test_save_meta(storage, tmp_path):
    meta = {
        "request_number": 1,
        "status": "completed",
        "tokens_used": {"input": 100, "output": 50, "total": 150},
    }
    path = await storage.save_meta("proj", 1, meta)
    assert path.name == "meta.json"
    loaded = json.loads(path.read_text())
    assert loaded["status"] == "completed"
    assert loaded["tokens_used"]["total"] == 150


async def test_full_session_structure(storage, tmp_path):
    """Verify the complete directory structure after a full session."""
    await storage.save_request("proj", 1, "Fix the bug")
    await storage.append_stream_log("proj", 1, "Looking at code...\n")
    await storage.save_interaction("proj", 1, 1, "Which file?", is_response=False)
    await storage.save_interaction("proj", 1, 1, "main.py", is_response=True)
    await storage.save_report("proj", 1, "Bug fixed.")
    await storage.save_meta("proj", 1, {"status": "completed"})

    d = tmp_path / "proj" / "request_1"
    assert (d / "request.md").exists()
    assert (d / "stream_log.md").exists()
    assert (d / "1.1.md").exists()
    assert (d / "1.1.response.md").exists()
    assert (d / "report.md").exists()
    assert (d / "meta.json").exists()
