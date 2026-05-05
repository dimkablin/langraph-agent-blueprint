"""Tool execution service that validates input, runs tools, formats records, and emits tool events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from claude_code_langgraph.models.messages import event
from claude_code_langgraph.tools.base import BaseTool, ToolExecutionContext
from claude_code_langgraph.tools.registry import ToolRegistry


class ToolExecutionService:
    """Validates, executes, persists, and formats tool results."""

    def __init__(self, registry: ToolRegistry, output_limit: int = 12000) -> None:
        self.registry = registry
        self.output_limit = output_limit

    def execute(self, tool_call: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        tool = self.registry.get(tool_call["name"])
        context = ToolExecutionContext(
            project_root=Path(state["project_root"]),
            cwd=Path(state["cwd"]),
            read_files=set(state.get("metadata", {}).get("read_files", [])),
            state=state,
        )
        try:
            parsed = tool.parse_input(tool_call.get("args", {}))
            output = tool.run(parsed, context)
            record = {
                "id": tool_call["id"],
                "name": tool.name,
                "status": "ok" if getattr(output, "ok", True) else "error",
                "content": getattr(output, "content", ""),
                "metadata": getattr(output, "metadata", {}) or {},
                "output": output.model_dump(mode="json"),
            }
            if tool.name == "todo_write":
                record["state_update"] = {"todos": record["output"].get("todos", [])}
            if tool.name in {"read_file", "edit_file", "write_file"}:
                record.setdefault("state_update", {}).setdefault("metadata", {})["read_files"] = sorted(context.read_files)
            if tool.name == "agent":
                record["state_update"] = {"child_runs": [record["output"]["child_run"]]}
            return record
        except (ValidationError, Exception) as exc:
            return {
                "id": tool_call["id"],
                "name": tool.name,
                "status": "error",
                "content": str(exc),
                "metadata": {"error_type": exc.__class__.__name__},
                "error": {"message": str(exc), "type": exc.__class__.__name__},
            }

    @staticmethod
    def started_event(tool_call: dict[str, Any]) -> dict[str, Any]:
        return event("tool_call_started", id=tool_call["id"], name=tool_call["name"])

    @staticmethod
    def finished_event(record: dict[str, Any]) -> dict[str, Any]:
        event_type = "tool_call_error" if record["status"] == "error" else "tool_call_finished"
        return event(event_type, id=record["id"], name=record["name"], status=record["status"])

