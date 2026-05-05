from __future__ import annotations

import fnmatch
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class SearchService:
    """Filesystem glob and grep service with ripgrep and Python fallback."""

    def __init__(self, force_python: bool = False) -> None:
        self.force_python = force_python

    def glob(self, root: str | Path, pattern: str) -> list[str]:
        root_path = Path(root).resolve()
        return [str(path) for path in root_path.glob(pattern)]

    def grep(
        self,
        root: str | Path,
        pattern: str,
        include: str | None = None,
        exclude: str | None = None,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        root_path = Path(root).resolve()
        if not self.force_python and shutil.which("rg"):
            return self._grep_rg(root_path, pattern, include, exclude, max_results)
        return self._grep_python(root_path, pattern, include, exclude, max_results)

    def _grep_rg(
        self,
        root: Path,
        pattern: str,
        include: str | None,
        exclude: str | None,
        max_results: int,
    ) -> list[dict[str, Any]]:
        command = ["rg", "--line-number", "--no-heading", pattern, str(root)]
        if include:
            command[1:1] = ["--glob", include]
        if exclude:
            command[1:1] = ["--glob", f"!{exclude}"]
        completed = subprocess.run(command, text=True, capture_output=True, timeout=10)
        matches: list[dict[str, Any]] = []
        for line in completed.stdout.splitlines()[:max_results]:
            parts = line.split(":", 2)
            if len(parts) == 3:
                matches.append({"path": parts[0], "line": int(parts[1]), "text": parts[2]})
        return matches

    def _grep_python(
        self,
        root: Path,
        pattern: str,
        include: str | None,
        exclude: str | None,
        max_results: int,
    ) -> list[dict[str, Any]]:
        compiled = re.compile(pattern)
        matches: list[dict[str, Any]] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if include and not fnmatch.fnmatch(rel, include):
                continue
            if exclude and fnmatch.fnmatch(rel, exclude):
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for idx, line in enumerate(lines, start=1):
                if compiled.search(line):
                    matches.append({"path": str(path), "line": idx, "text": line})
                    if len(matches) >= max_results:
                        return matches
        return matches

