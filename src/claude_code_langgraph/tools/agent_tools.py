"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel

from claude_code_langgraph.services.agent_service import AgentService

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class AgentInput(BaseModel):
    """Pydantic input schema for the agent operation."""
    prompt: str
    agent_type: str = "default"


class AgentOutput(ToolOutput):
    """Pydantic output schema for the agent operation."""
    child_run: dict[str, object]


class AgentTool(BaseTool[AgentInput, AgentOutput]):
    """Model-callable tool that delegates a prompt to the subagent service."""
    name = "agent"
    description = "Run a child graph/subagent and merge its result into parent state."
    input_schema = AgentInput
    output_schema = AgentOutput
    safety = ToolSafety.AGENT
    is_read_only = False
    requires_permission = False

    def __init__(self, agent_service: AgentService) -> None:
        self.agent_service = agent_service

    def run(self, data: AgentInput, context: ToolExecutionContext) -> AgentOutput:
        child = self.agent_service.run_child(data.prompt, context.state)
        return AgentOutput(child_run=child, content=child["result"], metadata={"agent_type": data.agent_type})

