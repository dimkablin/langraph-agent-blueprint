"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata

from .base import BaseTool, ToolExecutionContext, ToolOutput


class TodoWriteInput(BaseModel):
    """Pydantic input schema for the todo write operation."""
    todos: list[dict[str, object]] = Field(default_factory=list)


class TodoWriteOutput(ToolOutput):
    """Pydantic output schema for the todo write operation."""
    todos: list[dict[str, object]]


class TodoWriteTool(BaseTool[TodoWriteInput, TodoWriteOutput]):
    """Model-callable tool that replaces the visible todo list in graph state."""
    name = "todo_write"
    description = "Update the visible todo list in graph state."
    input_schema = TodoWriteInput
    output_schema = TodoWriteOutput
    permission = ToolPermissionMetadata(action="todo", risk="low", requires_permission=False, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="todo", state_effects=["replace_todos"])

    def run(self, data: TodoWriteInput, context: ToolExecutionContext) -> TodoWriteOutput:
        return TodoWriteOutput(todos=data.todos, content=f"Updated {len(data.todos)} todos")

