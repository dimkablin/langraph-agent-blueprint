"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def error_recovery_node(state: dict, deps: AppDependencies) -> dict:
    errors = state.get("errors", [])
    latest = errors[-1] if errors else {"message": "Unknown error"}
    final = f"Recovered from error: {latest.get('message')}"
    return {
        "pending_tool_calls": [],
        "final_response": final,
        "ui_events": [event("error", **latest), event("final_response", content=final)],
    }

