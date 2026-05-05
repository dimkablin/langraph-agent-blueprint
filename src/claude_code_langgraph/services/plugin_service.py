from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_code_langgraph.models.schemas import PluginManifest


class PluginService:
    """Discovers plugin manifests and exposes declared contributions."""

    def __init__(self, plugin_paths: list[str | Path]) -> None:
        self.plugin_paths = [Path(path) for path in plugin_paths]

    def discover(self) -> dict[str, Any]:
        plugins: list[PluginManifest] = []
        errors: list[dict[str, str]] = []
        for root in self.plugin_paths:
            if not root.exists():
                continue
            for manifest_path in root.rglob("plugin.json"):
                try:
                    plugins.append(PluginManifest.model_validate_json(manifest_path.read_text(encoding="utf-8")))
                except Exception as exc:
                    errors.append({"path": str(manifest_path), "error": str(exc)})
        return {
            "plugins": [plugin.model_dump() for plugin in plugins],
            "errors": errors,
            "commands": [command for plugin in plugins for command in plugin.commands],
            "skills": [skill for plugin in plugins for skill in plugin.skills],
            "tools": [tool for plugin in plugins for tool in plugin.tools],
            "hooks": [hook for plugin in plugins for hook in plugin.hooks],
            "mcp": [plugin.mcp for plugin in plugins if plugin.mcp],
        }

