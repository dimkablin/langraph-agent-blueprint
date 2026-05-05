from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def persist_session_node(state: dict, deps: AppDependencies) -> dict:
    metadata = {
        "session_id": state["session_id"],
        "thread_id": state["thread_id"],
        "project_root": state["project_root"],
        "usage": state.get("usage", {}),
        "model": state.get("metadata", {}).get("model_name"),
    }
    deps.session_storage.create_session(state["project_root"], state["session_id"], metadata)
    deps.session_storage.save_messages(state["project_root"], state["session_id"], state.get("messages", []))
    deps.session_storage.save_json(state["project_root"], state["session_id"], "todos.json", state.get("todos", []))
    deps.session_storage.save_json(state["project_root"], state["session_id"], "memory_refs.json", state.get("memory", {}))
    for item in state.get("ui_events", []):
        deps.session_storage.append_event(state["project_root"], state["session_id"], item)
    return {"ui_events": [event("session_persisted", session_id=state["session_id"])]}

