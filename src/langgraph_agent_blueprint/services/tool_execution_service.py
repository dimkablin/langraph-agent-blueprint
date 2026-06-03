"""Tool execution service that validates input, runs tools, formats records, and emits tool events."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from langgraph_agent_blueprint.models import AgentActivityEvent, FileSnapshotRecord, ToolCall, ToolResult, ToolStateEffect, dump_model, event
from langgraph_agent_blueprint.storage import SessionStorage
from langgraph_agent_blueprint.tools import ToolExecutionContext, ToolRegistry
from langgraph_agent_blueprint.tools.base import freeze_context_value
from langgraph_agent_blueprint.utils.ids import new_id
from langgraph_agent_blueprint.utils.paths import resolve_under_root
from langgraph_agent_blueprint.utils.truncation import truncate_text


class ToolExecutionService:
    """Validates, executes, persists, and formats tool results."""

    def __init__(self, registry: ToolRegistry, output_limit: int = 12000, session_storage: SessionStorage | None = None) -> None:
        self.registry = registry
        self.output_limit = output_limit
        self.session_storage = session_storage

    def execute(self, tool_call: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Validate one tool call, run the tool, and format a graph/persistence record."""

        call = ToolCall.model_validate(tool_call)
        tool = self.registry.get(call.name)
        context = self._context_for_state(state)
        try:
            parsed = tool.parse_input(call.args)
            snapshot = self._capture_file_snapshot(tool, parsed, call, context)
            output = tool.run(parsed, context)
            record = self._record_for_output(call, tool, output)
            if snapshot is not None:
                record["metadata"] = {**record["metadata"], "snapshot": snapshot.public_info().model_dump(mode="json")}
            result = ToolResult.model_validate(record)
            if result.status == "ok":
                effects = tool.state_effects(tool_call=call, result=result, output=output, state=state)
                state_update = apply_tool_state_effects(effects, state, context)
                if state_update:
                    record["state_update"] = state_update
            return dump_model(ToolResult.model_validate(record))
        except (ValidationError, Exception) as exc:
            return self._error_record(call, tool, exc)

    def execute_with_activity(
        self,
        tool_call: dict[str, Any],
        state: dict[str, Any],
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Execute one tool call and return its regular record plus public activity events."""

        call = ToolCall.model_validate(tool_call)
        tool = self.registry.get(call.name)
        context = self._context_for_state(state)
        parsed: Any | None = None
        events: list[dict[str, Any]] = []
        try:
            parsed = tool.parse_input(call.args)
            started_event = _runtime_event_with_activity(
                "tool_call_started",
                tool.build_activity_started_event(tool_call=call, data=parsed, context=context),
                id=call.id,
                name=call.name,
            )
            events.append(started_event)
            if on_event is not None:
                on_event(started_event)
            snapshot = self._capture_file_snapshot(tool, parsed, call, context)
            output = tool.run(parsed, context)
            record = self._record_for_output(call, tool, output)
            if snapshot is not None:
                record["metadata"] = {**record["metadata"], "snapshot": snapshot.public_info().model_dump(mode="json")}
            result = ToolResult.model_validate(record)
            if result.status == "ok":
                effects = tool.state_effects(tool_call=call, result=result, output=output, state=state)
                state_update = apply_tool_state_effects(effects, state, context)
                if state_update:
                    record["state_update"] = state_update
            event_type = "tool_call_error" if result.status == "error" else "tool_call_finished"
            events.append(
                _runtime_event_with_activity(
                    event_type,
                    tool.build_activity_completed_event(tool_call=call, data=parsed, output=output, context=context),
                    id=result.id,
                    name=result.name,
                    status=result.status,
                )
            )
            return dump_model(ToolResult.model_validate(record)), events
        except (ValidationError, Exception) as exc:
            record = self._error_record(call, tool, exc)
            events.append(
                _runtime_event_with_activity(
                    "tool_call_error",
                    tool.build_activity_failed_event(tool_call=call, data=parsed, error=exc, context=context),
                    id=call.id,
                    name=call.name,
                    status="error",
                )
            )
            return record, events

    def _context_for_state(self, state: dict[str, Any]) -> ToolExecutionContext:
        return ToolExecutionContext(
            project_root=Path(state["project_root"]),
            cwd=Path(state["cwd"]),
            session_id=str(state.get("session_id", "")),
            thread_id=str(state["thread_id"]) if state.get("thread_id") else None,
            read_files=tuple(str(item) for item in state.get("metadata", {}).get("read_files", [])),
            metadata=freeze_context_value(state.get("metadata", {})),
            active_skill=freeze_context_value(state.get("active_skill")) if isinstance(state.get("active_skill"), dict) else None,
        )

    def _record_for_output(self, call: ToolCall, tool: Any, output: Any) -> dict[str, Any]:
        raw_content = str(getattr(output, "content", "") or "")
        content, truncated = truncate_text(raw_content, self.output_limit)
        metadata = _metadata_for_output(output)
        if truncated:
            metadata = {
                **metadata,
                "content_truncated": True,
                "original_content_chars": len(raw_content),
                "content_limit_chars": self.output_limit,
            }
        output_payload = output.model_dump(mode="json")
        if truncated and isinstance(output_payload, dict) and "content" in output_payload:
            output_payload = {**output_payload, "content": content}
        return {
            "id": call.id,
            "name": tool.name,
            "status": "ok" if getattr(output, "ok", True) else "error",
            "content": content,
            "metadata": metadata,
            "output": output_payload,
        }

    def _error_record(self, call: ToolCall, tool: Any, exc: BaseException) -> dict[str, Any]:
        raw_content = str(exc)
        content, truncated = truncate_text(raw_content, self.output_limit)
        metadata: dict[str, Any] = {"error_type": exc.__class__.__name__}
        if truncated:
            metadata.update(
                {
                    "content_truncated": True,
                    "original_content_chars": len(raw_content),
                    "content_limit_chars": self.output_limit,
                }
            )
        return dump_model(
            ToolResult(
                id=call.id,
                name=tool.name,
                status="error",
                content=content,
                metadata=metadata,
                error={"message": content, "type": exc.__class__.__name__},
            )
        )

    def _capture_file_snapshot(self, tool: Any, parsed: Any, call: ToolCall, context: ToolExecutionContext) -> FileSnapshotRecord | None:
        if self.session_storage is None or not _requires_file_snapshot(tool, parsed):
            return None
        target = resolve_under_root(getattr(parsed, "path"), context.project_root)
        existed = target.exists() and target.is_file()
        content = target.read_text(encoding="utf-8") if existed else None
        snapshot = FileSnapshotRecord(
            snapshot_id=new_id("snapshot"),
            session_id=context.session_id,
            path=target.relative_to(context.project_root).as_posix(),
            existed=existed,
            content=content,
            tool_call_id=call.id,
            tool_name=tool.name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        payload = self.session_storage.save_file_snapshot(context.project_root, context.session_id, snapshot.model_dump(mode="json"))
        return FileSnapshotRecord.model_validate(payload)

    @staticmethod
    def started_event(tool_call: dict[str, Any]) -> dict[str, Any]:
        call = ToolCall.model_validate(tool_call)
        return event("tool_call_started", id=call.id, name=call.name)

    @staticmethod
    def finished_event(record: dict[str, Any]) -> dict[str, Any]:
        result = ToolResult.model_validate(record)
        event_type = "tool_call_error" if result.status == "error" else "tool_call_finished"
        return event(event_type, id=result.id, name=result.name, status=result.status)


def _runtime_event_with_activity(event_type: str, activity: AgentActivityEvent, **data: Any) -> dict[str, Any]:
    return event(event_type, **data, activity=activity.model_dump(mode="json"))


def _requires_file_snapshot(tool: Any, parsed: Any) -> bool:
    runtime = getattr(tool, "runtime", None)
    permission = getattr(tool, "permission", None)
    return (
        getattr(runtime, "kind", None) == "file"
        and getattr(permission, "action", None) in {"write", "edit"}
        and hasattr(parsed, "path")
    )


def _metadata_for_output(output: Any) -> dict[str, Any]:
    metadata = getattr(output, "metadata", {}) or {}
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


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

