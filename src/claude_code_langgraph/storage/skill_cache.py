"""Storage-layer module for persisting sessions, memory, config, transcripts, and capability caches."""

from __future__ import annotations

from pathlib import Path


class SkillCache:
    """Placeholder cache path provider for resolved skill metadata."""

    def __init__(self, storage_dir: str | Path) -> None:
        self.storage_dir = Path(storage_dir)

    def path(self) -> Path:
        return self.storage_dir / "skill_cache.json"

