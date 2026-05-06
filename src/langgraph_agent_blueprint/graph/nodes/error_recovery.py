"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point
from langgraph_agent_blueprint.models.messages import event


def error_recovery_node(state: dict, deps: AppDependencies) -> dict:
    """Turn the latest recoverable graph error into a final user-visible response."""

    errors = state.get("errors", [])
    latest = errors[-1] if errors else {"message": "Unknown error"}
    final = f"Recovered from error: {latest.get('message')}"
    hook_update = run_hook_point(deps, state, "error", metadata={"error": latest})
    return merge_updates(hook_update, {
        "pending_tool_calls": [],
        "final_response": final,
        "ui_events": [event("error", **latest), event("final_response", content=final)],
    })

