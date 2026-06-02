"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from time import perf_counter

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.graph.instrumentation import duration_ms, runtime_metrics_update
from langgraph_agent_blueprint.graph.run_control import cancellation_update
from langgraph_agent_blueprint.models import ToolCall, ToolResult, event, tool_result_to_tool_message, validate_list

RECOVERABLE_TOOL_ERROR_LIMIT = 3


def tool_executor_node(state: dict, deps: AppDependencies) -> dict:
    """Execute approved pending tool calls and append provider-compatible tool results.

    Tool records are persisted immediately, state updates from tools are merged into graph state,
    and each result receives a matching ToolMessage for the next model turn.
    """

    cancelled = cancellation_update(state, deps, node="tool_executor")
    if cancelled is not None:
        return cancelled
    calls = validate_list(ToolCall, state.get("pending_tool_calls", []))
    events = []
    results = []
    errors = []
    todos = state.get("todos", [])
    child_runs = []
    metadata = dict(state.get("metadata", {}))
    messages = []
    tool_durations = []
    recoverable_error_count = int(metadata.get("recoverable_tool_error_count", 0) or 0)
    for call in calls:
        call_payload = call.model_dump(mode="json")
        tool = deps.tool_registry.get(call.name)
        is_mcp = tool.runtime.kind == "mcp" or tool.runtime.route == "mcp_graph"
        mcp_metadata = tool.metadata().get("mcp", {}) if is_mcp else {}
        if is_mcp:
            events.append(
                event(
                    "mcp_tool_call_started",
                    id=call.id,
                    name=call.name,
                    server_name=mcp_metadata.get("server_name"),
                    tool_name=mcp_metadata.get("tool_name"),
                )
            )
        tool_start = perf_counter()
        record, activity_events = deps.tool_execution_service.execute_with_activity(call_payload, state)
        tool_duration_ms = duration_ms(tool_start)
        tool_durations.append({"id": call.id, "name": call.name, "duration_ms": tool_duration_ms})
        _attach_tool_duration(activity_events, call.id, tool_duration_ms)
        result = ToolResult.model_validate(record)
        record["metadata"] = {**dict(record.get("metadata", {}) or {}), "duration_ms": tool_duration_ms}
        results.append(record)
        messages.append(tool_result_to_tool_message(result))
        events.extend(activity_events)
        if is_mcp:
            events.append(
                event(
                    "mcp_tool_call_error" if result.status == "error" else "mcp_tool_call_finished",
                    id=result.id,
                    name=result.name,
                    status=result.status,
                    duration_ms=tool_duration_ms,
                    server_name=mcp_metadata.get("server_name"),
                    tool_name=mcp_metadata.get("tool_name"),
                )
            )
        deps.session_storage.append_tool_call(state["project_root"], state["session_id"], record)
        state_update = record.get("state_update", {})
        if "todos" in state_update:
            todos = state_update["todos"]
        if "child_runs" in state_update:
            child_runs.extend(state_update["child_runs"])
        if "metadata" in state_update:
            metadata.update(state_update["metadata"])
        snapshot = result.metadata.get("snapshot") if isinstance(result.metadata, dict) else None
        if isinstance(snapshot, dict):
            metadata["file_snapshots"] = _append_file_snapshot(metadata.get("file_snapshots", []), snapshot)
        if record.get("error"):
            recoverable_error_count += 1
            metadata["recoverable_tool_error_count"] = recoverable_error_count
            if recoverable_error_count > RECOVERABLE_TOOL_ERROR_LIMIT:
                errors.append(_terminal_recoverable_error_payload(record, recoverable_error_count))
        else:
            recoverable_error_count = 0
            metadata.pop("recoverable_tool_error_count", None)
    update = {
        "pending_tool_calls": [],
        "tool_results": results,
        "messages": messages,
        "todos": todos,
        "child_runs": child_runs,
        "metadata": metadata,
        "errors": errors,
        "ui_events": events,
        **runtime_metrics_update(state, {}, extra_metrics={"tool_durations_ms": tool_durations}),
    }
    active_tool = results[0] if results else None
    post_update = run_hook_point(deps, state_with_update(state, update), "post_tool", active_tool=active_tool)
    return merge_updates(update, post_update)


def _attach_tool_duration(events: list[dict], tool_call_id: str, duration_ms: float) -> None:
    for item in events:
        if item.get("type") not in {"tool_call_finished", "tool_call_error"}:
            continue
        data = item.get("data")
        if isinstance(data, dict) and data.get("id") == tool_call_id:
            data["duration_ms"] = duration_ms


def _error_payload(record: dict) -> dict:
    error = record.get("error")
    if isinstance(error, dict):
        return dict(error)
    return {"message": str(error or record.get("content") or "Tool execution failed"), "type": "ToolExecutionError"}


def _terminal_recoverable_error_payload(record: dict, attempts: int) -> dict:
    payload = _error_payload(record)
    original_message = str(payload.get("message") or record.get("content") or "Tool execution failed")
    tool_name = str(record.get("name") or "tool")
    payload.update(
        {
            "message": (
                f"Maximum recoverable tool error attempts exceeded after {attempts} failed tool calls. "
                f"Last {tool_name} error: {original_message}"
            ),
            "recoverable": False,
            "tool_call_id": record.get("id"),
            "tool_name": record.get("name"),
            "recoverable_tool_error_limit": RECOVERABLE_TOOL_ERROR_LIMIT,
            "recoverable_tool_error_count": attempts,
        }
    )
    return payload


def _append_file_snapshot(current: object, snapshot: dict) -> list[dict]:
    snapshots = list(current) if isinstance(current, list) else []
    snapshot_id = snapshot.get("snapshot_id")
    if snapshot_id and all(item.get("snapshot_id") != snapshot_id for item in snapshots if isinstance(item, dict)):
        snapshots.append(snapshot)
    return snapshots
