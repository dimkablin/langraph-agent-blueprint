from __future__ import annotations

from pathlib import Path


class PluginCache:
    """Placeholder cache path provider for plugin manifests."""

    def __init__(self, storage_dir: str | Path) -> None:
        self.storage_dir = Path(storage_dir)

    def path(self) -> Path:
        return self.storage_dir / "plugin_cache.json"

