"""High-level session lifecycle service over filesystem-backed SessionStorage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_code_langgraph.storage.session_storage import SessionStorage


class SessionService:
    """High-level session lifecycle operations."""

    def __init__(self, storage: SessionStorage) -> None:
        self.storage = storage

    def resume(self, project_root: str | Path, session_id: str) -> dict[str, Any]:
        return self.storage.load_session(project_root, session_id)

    def list(self, project_root: str | Path | None = None) -> list[dict[str, Any]]:
        return self.storage.list_sessions(project_root)

    def clear(self, project_root: str | Path, session_id: str) -> None:
        self.storage.clear_session(project_root, session_id)

