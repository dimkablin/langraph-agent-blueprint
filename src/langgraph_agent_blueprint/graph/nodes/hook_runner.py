"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies


def hook_runner_node(state: dict, deps: AppDependencies) -> dict:
    events = deps.hook_service.run("post_turn", {"session_id": state.get("session_id"), "state": state})
    return {"hooks_state": {"last_hook_count": len(events)}, "ui_events": events}

