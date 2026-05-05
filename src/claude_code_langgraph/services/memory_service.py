from __future__ import annotations

from pathlib import Path

from claude_code_langgraph.storage.memory_storage import MemoryStorage


class MemoryService:
    """Memory service for user, project, and session scopes."""

    def __init__(self, storage_dir: str | Path) -> None:
        self.storage = MemoryStorage(storage_dir)

    def load_memory(self, project_root: str | Path | None = None, session_id: str | None = None) -> dict[str, str]:
        memory = {
            "user": self.storage.read("user"),
            "project": self.storage.read("project"),
            "session": self.storage.read(f"session-{session_id}") if session_id else "",
        }
        return memory

    def remember(self, scope: str, text: str) -> Path:
        return self.storage.append(scope, text)

    def build_context(self, memory: dict[str, str], budget: int = 2000) -> str:
        parts = []
        for scope in ["user", "project", "session"]:
            content = memory.get(scope, "").strip()
            if content:
                parts.append(f"{scope} memory:\n{content}")
        context = "\n\n".join(parts)
        return context[:budget]

