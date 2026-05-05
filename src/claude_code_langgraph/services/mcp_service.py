"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MCPToolDefinition:
    """Internal description of an MCP-provided tool before it is wrapped as a BaseTool."""
    name: str
    description: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    input_schema: dict[str, Any]


class MCPService:
    """Minimal MCP registry/discovery abstraction with safe disabled default."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._mock_tools: dict[str, MCPToolDefinition] = {}

    def register_mock_tool(self, name: str, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self._mock_tools[name] = MCPToolDefinition(
            name=name,
            description=f"Mock MCP tool {name}",
            handler=handler,
            input_schema={"type": "object"},
        )

    def discover(self) -> dict[str, Any]:
        return {"tools": dict(self._mock_tools), "resources": {}, "prompts": {}}

