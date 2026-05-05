"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from claude_code_langgraph.utils.paths import resolve_under_root


class FileService:
    """Safe filesystem operations confined to a project root by default."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve()

    def resolve(self, path: str | Path) -> Path:
        return resolve_under_root(path, self.project_root)

    def read_text(self, path: str | Path, offset: int | None = None, limit: int | None = None) -> str:
        """Read UTF-8-ish text with binary-file guard and optional one-based line slicing."""

        target = self.resolve(path)
        if target.is_dir():
            raise IsADirectoryError(str(target))
        data = target.read_bytes()
        if b"\x00" in data[:4096]:
            raise ValueError(f"Refusing to read binary file: {target}")
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        if offset is not None or limit is not None:
            start = max((offset or 1) - 1, 0)
            end = start + limit if limit else None
            lines = lines[start:end]
            return "\n".join(lines)
        return text

    def write_text(self, path: str | Path, content: str) -> dict[str, Any]:
        target = self.resolve(path)
        old = target.read_text(encoding="utf-8") if target.exists() and target.is_file() else ""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": str(target), "diff": self.diff(old, content, str(target))}

    def edit_text(self, path: str | Path, old_text: str, new_text: str) -> dict[str, Any]:
        """Replace the first exact occurrence of old text and return a unified diff."""

        target = self.resolve(path)
        content = target.read_text(encoding="utf-8")
        if old_text not in content:
            raise ValueError("old_text was not found exactly once or at all")
        updated = content.replace(old_text, new_text, 1)
        target.write_text(updated, encoding="utf-8")
        return {"path": str(target), "diff": self.diff(content, updated, str(target))}

    def read_notebook(self, path: str | Path) -> dict[str, Any]:
        target = self.resolve(path)
        return json.loads(target.read_text(encoding="utf-8"))

    def write_notebook(self, path: str | Path, notebook: dict[str, Any]) -> None:
        target = self.resolve(path)
        target.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def diff(old: str, new: str, filename: str) -> str:
        return "\n".join(
            difflib.unified_diff(
                old.splitlines(),
                new.splitlines(),
                fromfile=f"{filename}:before",
                tofile=f"{filename}:after",
                lineterm="",
            )
        )

