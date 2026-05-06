"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models.base import validate_list
from langgraph_agent_blueprint.models.tools import ToolCall, ToolResult, tool_result_to_tool_message


def tool_executor_node(state: dict, deps: AppDependencies) -> dict:
    """Execute approved pending tool calls and append provider-compatible tool results.

    Tool records are persisted immediately, state updates from tools are merged into graph state,
    and each result receives a matching ToolMessage for the next model turn.
    """

    calls = validate_list(ToolCall, state.get("pending_tool_calls", []))
    events = []
    results = []
    errors = []
    todos = state.get("todos", [])
    child_runs = []
    metadata = dict(state.get("metadata", {}))
    messages = []
    for call in calls:
        call_payload = call.model_dump(mode="json")
        events.append(deps.tool_execution_service.started_event(call_payload))
        record = deps.tool_execution_service.execute(call_payload, state)
        result = ToolResult.model_validate(record)
        results.append(record)
        messages.append(tool_result_to_tool_message(result))
        events.append(deps.tool_execution_service.finished_event(record))
        deps.session_storage.append_tool_call(state["project_root"], state["session_id"], record)
        state_update = record.get("state_update", {})
        if "todos" in state_update:
            todos = state_update["todos"]
        if "child_runs" in state_update:
            child_runs.extend(state_update["child_runs"])
        if "metadata" in state_update:
            metadata.update(state_update["metadata"])
        if record.get("error"):
            errors.append(record["error"])
    update = {
        "pending_tool_calls": [],
        "tool_results": results,
        "messages": messages,
        "todos": todos,
        "child_runs": child_runs,
        "metadata": metadata,
        "errors": errors,
        "ui_events": events,
    }
    active_tool = results[0] if results else None
    post_update = run_hook_point(deps, state_with_update(state, update), "post_tool", active_tool=active_tool)
    return merge_updates(update, post_update)
