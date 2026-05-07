"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models.subagents import SubagentRequest
from langgraph_agent_blueprint.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services.agent_service import AgentService

from .base import BaseTool, ToolExecutionContext, ToolOutput


class AgentInput(BaseModel):
    """Pydantic input schema for the agent operation."""

    prompt: str
    name: str | None = None
    purpose: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    max_turns: int = 8
    timeout_seconds: float | None = 300.0
    inherit_memory: bool = True
    inherit_todos: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_type: str = "default"

    def to_request(self) -> SubagentRequest:
        """Convert tool input into the typed subagent request boundary."""

        return SubagentRequest(
            prompt=self.prompt,
            name=self.name or (None if self.agent_type == "default" else self.agent_type),
            purpose=self.purpose,
            allowed_tools=list(self.allowed_tools),
            max_turns=self.max_turns,
            timeout_seconds=self.timeout_seconds,
            inherit_memory=self.inherit_memory,
            inherit_todos=self.inherit_todos,
            metadata=dict(self.metadata),
        )


class AgentOutput(ToolOutput):
    """Pydantic output schema for the agent operation."""

    child_run: dict[str, object]


class AgentTool(BaseTool[AgentInput, AgentOutput]):
    """Model-callable tool that delegates a prompt to the subagent service."""
    name = "agent"
    description = "Run a child graph/subagent and merge its result into parent state."
    input_schema = AgentInput
    output_schema = AgentOutput
    permission = ToolPermissionMetadata(action="agent", risk="medium", requires_permission=False, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="agent", route="agent_graph", state_effects=["append_child_run"])

    def __init__(self, agent_service: AgentService) -> None:
        self.agent_service = agent_service

    def run(self, data: AgentInput, context: ToolExecutionContext) -> AgentOutput:
        request = data.to_request()
        return AgentOutput(
            ok=False,
            child_run={"request": request.model_dump(mode="json"), "status": "unavailable"},
            content="AgentTool is graph-routed; direct execution is not supported.",
            metadata={"agent_type": data.agent_type, "route": "agent_graph"},
        )

