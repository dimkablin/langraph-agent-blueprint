"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from time import perf_counter

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.instrumentation import duration_ms, runtime_metrics_update
from langgraph_agent_blueprint.models import event


def persist_session_node(state: dict, deps: AppDependencies) -> dict:
    """Persist the current graph turn without changing workflow routing.

    Metadata, messages, todos, memory references, and all accumulated UI events are written through
    SessionStorage; storage-level event ids prevent duplicate event rows.
    """

    persistence_start = perf_counter()
    state_metadata = {key: value for key, value in state.get("metadata", {}).items() if key not in {"streaming_enabled"}}
    metadata = {
        **state_metadata,
        "session_id": state["session_id"],
        "thread_id": state["thread_id"],
        "project_id": state.get("project_id"),
        "project_root": state["project_root"],
        "workspace": state.get("workspace", {}),
        "usage": state.get("usage", {}),
        "model": state_metadata.get("model_name"),
    }
    deps.session_storage.create_session(state["project_root"], state["session_id"], metadata)
    deps.session_storage.save_messages(state["project_root"], state["session_id"], state.get("messages", []))
    deps.session_storage.save_json(state["project_root"], state["session_id"], "todos.json", state.get("todos", []))
    deps.session_storage.save_json(state["project_root"], state["session_id"], "memory_refs.json", state.get("memory", {}))
    for item in state.get("ui_events", []):
        deps.session_storage.append_event(state["project_root"], state["session_id"], item)
    persistence_duration_ms = duration_ms(persistence_start)
    persisted_event = event(
        "session_persisted",
        session_id=state["session_id"],
        persistence_duration_ms=persistence_duration_ms,
        persisted_event_count=len(state.get("ui_events", []) or []),
    )
    deps.session_storage.append_event(state["project_root"], state["session_id"], persisted_event)
    return {
        "ui_events": [persisted_event],
        **runtime_metrics_update(
            state,
            {},
            extra_metrics={
                "persistence_duration_ms": persistence_duration_ms,
                "persisted_event_count": len(state.get("ui_events", []) or []),
            },
        ),
    }
