from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class TodoWriteInput(BaseModel):
    todos: list[dict[str, object]] = Field(default_factory=list)


class TodoWriteOutput(ToolOutput):
    todos: list[dict[str, object]]


class TodoWriteTool(BaseTool[TodoWriteInput, TodoWriteOutput]):
    name = "todo_write"
    description = "Update the visible todo list in graph state."
    input_schema = TodoWriteInput
    output_schema = TodoWriteOutput
    safety = ToolSafety.WRITE
    is_read_only = False
    requires_permission = False

    def run(self, data: TodoWriteInput, context: ToolExecutionContext) -> TodoWriteOutput:
        return TodoWriteOutput(todos=data.todos, content=f"Updated {len(data.todos)} todos")

