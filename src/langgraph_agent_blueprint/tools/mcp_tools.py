"""ToolRegistry adapter for tools discovered from MCP servers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models.mcp import MCPToolContribution
from langgraph_agent_blueprint.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services.mcp_service import MCPService

from .base import BaseTool, ToolExecutionContext, ToolOutput


class MCPInput(BaseModel):
    """Generic MCP input boundary.

    Provider calls pass tool arguments directly. The adapter keeps this model as
    a typed boundary while advertising each server-provided JSON schema in
    `metadata()`.
    """

    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPOutput(ToolOutput):
    """Structured output from an MCP tool call."""

    result: dict[str, Any] = Field(default_factory=dict)


class MCPToolAdapter(BaseTool[MCPInput, MCPOutput]):
    """Expose a discovered MCP tool through the normal BaseTool interface."""

    input_schema = MCPInput
    output_schema = MCPOutput
    permission = ToolPermissionMetadata(
        action="mcp",
        risk="high",
        requires_permission=True,
        external=True,
        reason="External MCP tool requires approval by default.",
    )
    runtime = ToolRuntimeMetadata(kind="mcp", route="mcp_graph")

    def __init__(self, contribution: MCPToolContribution | dict[str, Any], service: MCPService) -> None:
        self.contribution = MCPToolContribution.model_validate(contribution)
        self.service = service
        self.name = self.contribution.registry_name
        self.description = self.contribution.description or f"MCP tool {self.contribution.tool_name}"

    def parse_input(self, data: dict[str, object]) -> MCPInput:
        if set(data) == {"arguments"} and isinstance(data.get("arguments"), dict):
            return MCPInput(arguments=dict(data["arguments"]))  # type: ignore[arg-type]
        return MCPInput(arguments=dict(data))

    def run(self, data: MCPInput, context: ToolExecutionContext) -> MCPOutput:
        result = self.service.call_tool(self.contribution.server_name, self.contribution.tool_name, data.arguments)
        return MCPOutput(
            ok=result.status == "ok",
            content=result.content,
            result=result.data,
            metadata={
                "server_name": result.server_name,
                "tool_name": result.tool_name,
                "external": True,
                "untrusted": True,
                **({"error": result.error} if result.error else {}),
            },
        )

    def metadata(self) -> dict[str, object]:
        data = super().metadata()
        data["input_schema"] = self.contribution.input_schema or {"type": "object", "properties": {}}
        data["output_schema"] = self.contribution.output_schema or {"type": "object"}
        data["mcp"] = {
            "server_name": self.contribution.server_name,
            "tool_name": self.contribution.tool_name,
            "registry_name": self.contribution.registry_name,
        }
        return data
