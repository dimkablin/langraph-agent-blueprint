"""Tool execution service that validates input, runs tools, formats records, and emits tool events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from langgraph_agent_blueprint.models import ToolCall, ToolResult, ToolStateEffect, dump_model, event
from langgraph_agent_blueprint.tools import BaseTool, ToolExecutionContext, ToolRegistry
from langgraph_agent_blueprint.tools.base import freeze_context_value


class ToolExecutionService:
    """Validates, executes, persists, and formats tool results."""

    def __init__(self, registry: ToolRegistry, output_limit: int = 12000) -> None:
        self.registry = registry
        self.output_limit = output_limit

    def execute(self, tool_call: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Validate one tool call, run the tool, and format a graph/persistence record."""

        call = ToolCall.model_validate(tool_call)
        tool = self.registry.get(call.name)
        context = ToolExecutionContext(
            project_root=Path(state["project_root"]),
            cwd=Path(state["cwd"]),
            session_id=str(state.get("session_id", "")),
            thread_id=str(state["thread_id"]) if state.get("thread_id") else None,
            read_files=tuple(str(item) for item in state.get("metadata", {}).get("read_files", [])),
            metadata=freeze_context_value(state.get("metadata", {})),
            active_skill=freeze_context_value(state.get("active_skill")) if isinstance(state.get("active_skill"), dict) else None,
        )
        try:
            parsed = tool.parse_input(call.args)
            output = tool.run(parsed, context)
            record: dict[str, Any] = {
                "id": call.id,
                "name": tool.name,
                "status": "ok" if getattr(output, "ok", True) else "error",
                "content": getattr(output, "content", ""),
                "metadata": getattr(output, "metadata", {}) or {},
                "output": output.model_dump(mode="json"),
            }
            result = ToolResult.model_validate(record)
            if result.status == "ok":
                effects = tool.state_effects(tool_call=call, result=result, output=output, state=state)
                state_update = apply_tool_state_effects(effects, state, context)
                if state_update:
                    record["state_update"] = state_update
            return dump_model(ToolResult.model_validate(record))
        except (ValidationError, Exception) as exc:
            return dump_model(
                ToolResult(
                    id=call.id,
                    name=tool.name,
                    status="error",
                    content=str(exc),
                    metadata={"error_type": exc.__class__.__name__},
                    error={"message": str(exc), "type": exc.__class__.__name__},
                )
            )

    @staticmethod
    def started_event(tool_call: dict[str, Any]) -> dict[str, Any]:
        call = ToolCall.model_validate(tool_call)
        return event("tool_call_started", id=call.id, name=call.name)

    @staticmethod
    def finished_event(record: dict[str, Any]) -> dict[str, Any]:
        result = ToolResult.model_validate(record)
        event_type = "tool_call_error" if result.status == "error" else "tool_call_finished"
        return event(event_type, id=result.id, name=result.name, status=result.status)


def apply_tool_state_effects(
    effects: list[ToolStateEffect],
    state: dict[str, Any],
    context: ToolExecutionContext,
) -> dict[str, Any]:
    """Convert typed tool state effects into a serializable graph state delta."""

    state_update: dict[str, Any] = {}
    read_files = set(context.read_files)
    for effect in effects:
        if effect.kind == "record_file_read":
            path = effect.data.get("path")
            if path:
                read_files.add(str(path))
            state_update.setdefault("metadata", {})["read_files"] = sorted(read_files)
        elif effect.kind in {"record_file_write", "record_file_edit"}:
            state_update.setdefault("metadata", {})["read_files"] = sorted(read_files)
        elif effect.kind == "replace_todos":
            state_update["todos"] = effect.data.get("todos", [])
        elif effect.kind == "append_child_run":
            child_run = effect.data.get("child_run")
            if child_run:
                state_update.setdefault("child_runs", []).append(child_run)
    return state_update

