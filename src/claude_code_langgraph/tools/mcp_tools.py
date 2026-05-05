"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from claude_code_langgraph.services.mcp_service import MCPToolDefinition

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class MCPInput(BaseModel):
    """Pydantic input schema for the m c p operation."""
    data: dict[str, Any] = Field(default_factory=dict)


class MCPOutput(ToolOutput):
    """Pydantic output schema for the m c p operation."""
    result: dict[str, Any] = Field(default_factory=dict)


class MCPToolAdapter(BaseTool[MCPInput, MCPOutput]):
    """Model-callable adapter that exposes an MCP tool definition through the BaseTool interface."""
    description = "Adapter around an MCP-provided tool."
    input_schema = MCPInput
    output_schema = MCPOutput
    safety = ToolSafety.MCP
    is_read_only = False
    requires_permission = True

    def __init__(self, definition: MCPToolDefinition) -> None:
        self.definition = definition
        self.name = f"mcp.{definition.name}"
        self.description = definition.description

    def run(self, data: MCPInput, context: ToolExecutionContext) -> MCPOutput:
        result = self.definition.handler(data.data)
        return MCPOutput(result=result, content=str(result))

