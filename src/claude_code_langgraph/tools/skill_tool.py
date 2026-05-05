"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel, Field

from claude_code_langgraph.services.skill_service import SkillInvocationService

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class SkillToolInput(BaseModel):
    """Pydantic input schema for the skill tool operation."""
    skill: str
    args: str = ""


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
    safety = ToolSafety.SKILL
    is_read_only = False
    requires_permission = False

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

