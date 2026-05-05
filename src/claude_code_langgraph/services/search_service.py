"""Search service implementing glob and grep through ripgrep or Python fallback."""

from __future__ import annotations

import fnmatch
import json
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
        """Search text under a root with ripgrep when available and Python fallback otherwise."""

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
        """Run ripgrep in JSON mode so Windows drive-letter paths parse safely."""

        command = ["rg", "--json", pattern, str(root)]
        if include:
            command[1:1] = ["--glob", include]
        if exclude:
            command[1:1] = ["--glob", f"!{exclude}"]
        completed = subprocess.run(command, text=True, capture_output=True, timeout=10)
        matches: list[dict[str, Any]] = []
        for line in completed.stdout.splitlines():
            if len(matches) >= max_results:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("type") != "match":
                continue
            data = payload.get("data", {})
            path_data = data.get("path", {})
            lines_data = data.get("lines", {})
            path = path_data.get("text", "") if isinstance(path_data, dict) else str(path_data)
            text = lines_data.get("text", "") if isinstance(lines_data, dict) else str(lines_data)
            matches.append({"path": path, "line": int(data.get("line_number", 0)), "text": text.rstrip("\r\n")})
        return matches

    def _grep_python(
        self,
        root: Path,
        pattern: str,
        include: str | None,
        exclude: str | None,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Pure-Python grep fallback used when ripgrep is unavailable or disabled."""

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
