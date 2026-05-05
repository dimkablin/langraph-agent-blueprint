"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from claude_code_langgraph.dependencies import AppDependencies


def tool_executor_node(state: dict, deps: AppDependencies) -> dict:
    calls = list(state.get("pending_tool_calls", []))
    events = []
    results = []
    errors = []
    todos = state.get("todos", [])
    child_runs = []
    metadata = dict(state.get("metadata", {}))
    messages = []
    for call in calls:
        events.append(deps.tool_execution_service.started_event(call))
        record = deps.tool_execution_service.execute(call, state)
        results.append(record)
        messages.append(_tool_message(record))
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
        "messages": messages,
        "todos": todos,
        "child_runs": child_runs,
        "metadata": metadata,
        "errors": errors,
        "ui_events": events,
    }


def _tool_message(record: dict) -> ToolMessage:
    content = json.dumps(
        {
            "name": record.get("name"),
            "status": record.get("status"),
            "content": record.get("content", ""),
            "metadata": record.get("metadata", {}),
        },
        ensure_ascii=False,
    )
    return ToolMessage(content=content, tool_call_id=str(record.get("id") or "unknown"))
