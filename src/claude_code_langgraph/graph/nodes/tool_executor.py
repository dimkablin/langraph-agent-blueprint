from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies


def tool_executor_node(state: dict, deps: AppDependencies) -> dict:
    calls = list(state.get("pending_tool_calls", []))
    events = []
    results = []
    errors = []
    todos = state.get("todos", [])
    child_runs = list(state.get("child_runs", []))
    metadata = dict(state.get("metadata", {}))
    for call in calls:
        events.append(deps.tool_execution_service.started_event(call))
        record = deps.tool_execution_service.execute(call, state)
        results.append(record)
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
    return {
        "pending_tool_calls": [],
        "tool_results": results,
        "todos": todos,
        "child_runs": child_runs,
        "metadata": metadata,
        "errors": errors,
        "ui_events": events,
    }

