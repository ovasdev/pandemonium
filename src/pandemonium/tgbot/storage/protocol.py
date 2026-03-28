"""Protocol storage — filesystem-based session logging."""

import asyncio
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class ProtocolStorage:
    """Writes session data to a structured directory tree."""

    def __init__(self, base_path: Path) -> None:
        self._base = base_path

    def _request_dir(self, project_id: str, number: int) -> Path:
        return self._base / project_id / f"request_{number}"

    def _ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def next_request_number(self, project_id: str) -> int:
        """Scan existing folders and return max + 1."""
        project_dir = self._base / project_id
        if not project_dir.exists():
            return 1
        pattern = re.compile(r"^request_(\d+)$")
        numbers: list[int] = []
        for child in project_dir.iterdir():
            if child.is_dir() and (m := pattern.match(child.name)):
                numbers.append(int(m.group(1)))
        return max(numbers, default=0) + 1

    async def save_request(
        self, project_id: str, number: int, content: str,
    ) -> Path:
        """Save the original user request as request.md."""
        d = self._request_dir(project_id, number)
        path = d / "request.md"
        await asyncio.to_thread(self._write_file, path, content)
        return path

    async def save_interaction(
        self,
        project_id: str,
        req_number: int,
        sub_number: int,
        content: str,
        is_response: bool,
    ) -> Path:
        """Save an interaction (question or response) as N.sub.md."""
        d = self._request_dir(project_id, req_number)
        suffix = ".response.md" if is_response else ".md"
        path = d / f"{req_number}.{sub_number}{suffix}"
        await asyncio.to_thread(self._write_file, path, content)
        return path

    async def append_stream_log(
        self, project_id: str, req_number: int, chunk: str,
    ) -> None:
        """Append a chunk to the stream log."""
        d = self._request_dir(project_id, req_number)
        path = d / "stream_log.md"
        await asyncio.to_thread(self._append_file, path, chunk)

    async def save_report(
        self, project_id: str, req_number: int, content: str,
    ) -> Path:
        """Save the final report as report.md."""
        d = self._request_dir(project_id, req_number)
        path = d / "report.md"
        await asyncio.to_thread(self._write_file, path, content)
        return path

    async def save_error(
        self, project_id: str, req_number: int, error: str,
    ) -> Path:
        """Save error details as error.md."""
        d = self._request_dir(project_id, req_number)
        path = d / "error.md"
        await asyncio.to_thread(self._write_file, path, error)
        return path

    async def save_meta(
        self, project_id: str, req_number: int, meta: dict,
    ) -> Path:
        """Save metadata as meta.json."""
        d = self._request_dir(project_id, req_number)
        path = d / "meta.json"
        text = json.dumps(meta, indent=2, ensure_ascii=False)
        await asyncio.to_thread(self._write_file, path, text)
        return path

    def _write_file(self, path: Path, content: str) -> None:
        self._ensure_dir(path.parent)
        path.write_text(content, encoding="utf-8")

    def _append_file(self, path: Path, content: str) -> None:
        self._ensure_dir(path.parent)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
