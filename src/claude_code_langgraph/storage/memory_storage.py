from __future__ import annotations

from pathlib import Path


class MemoryStorage:
    """Markdown-backed memory storage."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def path_for(self, scope: str) -> Path:
        return self.root / "memory" / f"{scope}.md"

    def read(self, scope: str) -> str:
        path = self.path_for(scope)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def append(self, scope: str, text: str) -> Path:
        path = self.path_for(scope)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        separator = "\n" if existing and not existing.endswith("\n") else ""
        path.write_text(existing + separator + f"- {text.strip()}\n", encoding="utf-8")
        return path

