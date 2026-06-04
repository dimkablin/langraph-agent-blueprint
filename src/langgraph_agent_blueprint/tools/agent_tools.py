"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from langgraph_agent_blueprint.models import RuntimeModel, SubagentRequest, ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services import AgentService

from .base import BaseTool, ToolExecutionContext, ToolOutput


class AgentInput(RuntimeModel):
    """Pydantic input schema for the agent operation."""

    prompt: str = Field(
        description="Concrete task for the child subagent, including relevant context, constraints, and acceptance criteria."
    )
    name: str | None = Field(
        default=None,
        description="Short visible subagent name, for example 'backend', 'frontend', or 'reviewer'.",
    )
    purpose: str | None = Field(
        default=None,
        description="One-sentence reason this subagent is being delegated a separate workstream.",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description=(
            "Optional snake_case allow-list of exact tool names available to the child subagent. "
            "Use the field name `allowed_tools`, never `allowedTools`. Leave empty only for the default read-only safe scope. "
            "This narrows child tool visibility; it does not bypass permission policy."
        ),
    )
    max_turns: int = Field(
        default=8,
        description="Maximum ReAct turns the child subagent may run before stopping.",
    )
    timeout_seconds: float | None = Field(
        default=300.0,
        description="Maximum wall-clock seconds allowed for the child subagent run.",
    )
    inherit_memory: bool = Field(
        default=True,
        description="Whether the child subagent receives parent memory context.",
    )
    inherit_todos: bool = Field(
        default=False,
        description="Whether the child subagent receives parent todo state.",
    )
    inherit_context: bool = Field(
        default=True,
        description="Whether the child subagent receives parent runtime context.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured metadata for observability and child-run bookkeeping.",
    )
    agent_type: str = Field(
        default="default",
        description="Child agent implementation type. Use 'default' unless a specific runtime agent type is required.",
    )

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
            inherit_context=self.inherit_context,
            metadata=dict(self.metadata),
        )


class AgentOutput(ToolOutput):
    """Pydantic output schema for the agent operation."""

    child_run: dict[str, object]


class AgentTool(BaseTool[AgentInput, AgentOutput]):
    """Model-callable tool that delegates a prompt to the subagent service."""

    name = "agent"
    description = (
        "Delegate work to a child subagent and merge its result into parent state. "
        "Use this tool whenever the user asks to create, run, spawn, or delegate subagents/agents, "
        "split work across frontend/backend or parallel workers, or start named child agents. "
        "If the child must edit files, write files, or run shell commands, pass a minimal `allowed_tools` list "
        "with exact tool names such as read_file, glob, grep, write_file, edit_file, bash, or powershell. "
        "Calling this tool is the action that starts a subagent; writing text such as "
        "'I will create subagents' does not start them."
    )
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

