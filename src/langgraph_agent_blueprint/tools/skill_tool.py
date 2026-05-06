"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services.skill_service import SkillInvocationService

from .base import BaseTool, ToolExecutionContext, ToolOutput


class SkillToolInput(BaseModel):
    """Pydantic input schema for the skill tool operation."""
    skill: str
    args: Any = ""


class SkillToolOutput(ToolOutput):
    """Pydantic output schema for the skill tool operation."""
    skill: str
    allowed_tools: list[str] = Field(default_factory=list)


class SkillTool(BaseTool[SkillToolInput, SkillToolOutput]):
    """Model-callable tool that routes named skill invocations back into the graph skill runtime."""
    name = "skill"
    description = "Invoke a named skill with arguments through the skill graph."
    input_schema = SkillToolInput
    output_schema = SkillToolOutput
    permission = ToolPermissionMetadata(action="skill", risk="low", requires_permission=False, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="skill", route="skill_graph")

    def __init__(self, skill_service: SkillInvocationService | None = None) -> None:
        self.skill_service = skill_service

    def run(self, data: SkillToolInput, context: ToolExecutionContext) -> SkillToolOutput:
        if self.skill_service is None:
            raise RuntimeError("SkillInvocationService is not configured")
        result = self.skill_service.invoke(data.skill, data.args, context.state)
        return SkillToolOutput(
            skill=data.skill,
            allowed_tools=result.get("allowed_tools", []),
            content=result.get("prompt", ""),
            metadata=result,
        )

