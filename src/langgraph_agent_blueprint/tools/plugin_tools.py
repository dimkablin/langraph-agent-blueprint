"""Declarative plugin tool adapters.

Plugin tools are intentionally data-only. They do not execute arbitrary plugin
Python/JS and can only serve manifest-declared static text or plugin-root files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models.plugins import PluginToolContribution

from .base import BaseTool, ToolExecutionContext, ToolOutput


class PluginToolInput(BaseModel):
    """Permissive input envelope for declarative plugin tools."""

    value: Any | None = None
    args: dict[str, Any] = Field(default_factory=dict)


class PluginToolOutput(ToolOutput):
    """Structured output returned by declarative plugin tools."""


class PluginToolAdapter(BaseTool[PluginToolInput, PluginToolOutput]):
    """Runtime adapter for one safe plugin tool contribution."""

    input_schema = PluginToolInput
    output_schema = PluginToolOutput

    def __init__(self, contribution: PluginToolContribution) -> None:
        self.contribution = contribution
        self.name = contribution.registry_name or f"plugin.{contribution.plugin_name}.{contribution.name}"
        self.description = contribution.description or f"{contribution.plugin_name} plugin tool"
        self.permission = contribution.permission
        self.runtime = contribution.runtime

    def run(self, data: PluginToolInput, context: ToolExecutionContext) -> PluginToolOutput:
        if not self.contribution.enabled or self.contribution.kind == "disabled_placeholder":
            return PluginToolOutput(ok=False, content=f"Plugin tool {self.name} is disabled.")
        if self.contribution.kind == "static_text":
            return PluginToolOutput(ok=True, content=self.contribution.response or "", metadata=self._metadata())
        if self.contribution.kind == "context_lookup":
            try:
                text = self._read_plugin_file()
            except Exception as exc:
                return PluginToolOutput(ok=False, content=str(exc), metadata=self._metadata())
            return PluginToolOutput(ok=True, content=text, metadata=self._metadata())
        return PluginToolOutput(ok=False, content=f"Unsupported plugin tool kind: {self.contribution.kind}", metadata=self._metadata())

    def _read_plugin_file(self) -> str:
        root = Path(str(self.contribution.metadata.get("root_path") or "")).resolve()
        if not root.exists():
            raise ValueError("Plugin root is unavailable")
        relative = self.contribution.path
        if not relative:
            raise ValueError("Plugin context_lookup tool requires a manifest path")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("Plugin tool path traversal rejected") from exc
        if not candidate.is_file():
            raise FileNotFoundError(relative)
        data = candidate.read_bytes()
        if b"\x00" in data[:4096]:
            raise ValueError("Refusing to return binary plugin file")
        return data[:200_000].decode("utf-8", errors="replace")

    def _metadata(self) -> dict[str, Any]:
        return {
            "plugin_name": self.contribution.plugin_name,
            "tool_name": self.contribution.name,
            "kind": self.contribution.kind,
        }

    def metadata(self) -> dict[str, object]:
        base = super().metadata()
        base["input_schema"] = self.contribution.input_schema or base["input_schema"]
        base["plugin"] = self._metadata()
        return base
