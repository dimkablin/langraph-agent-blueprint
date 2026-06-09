"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point
from langgraph_agent_blueprint.models import AgentActivityEvent, AgentActivitySource, ErrorStreamEvent, event, stream_event_payload
from langgraph_agent_blueprint.utils.activity import safe_activity_data


def error_recovery_node(state: dict, deps: AppDependencies) -> dict:
    """Turn the latest recoverable graph error into a final user-visible response."""

    errors = state.get("errors", [])
    latest = errors[-1] if errors else {"message": "Unknown error"}
    final = f"Recovered from error: {latest.get('message')}"
    hook_update = run_hook_point(deps, state, "error", metadata={"error": latest})
    failed_activity = AgentActivityEvent(
        type="runtime.run.failed",
        source=AgentActivitySource(kind="runtime", component="AssistantGraphRuntime"),
        category="runtime",
        status="error",
        title="Run error",
        summary=str(latest.get("message") or "Unknown error"),
        data=safe_activity_data(latest),
    )
    return merge_updates(hook_update, {
        "pending_tool_calls": [],
        "final_response": final,
        "ui_events": [
            event(
                "error",
                **latest,
                activity=failed_activity.model_dump(mode="json"),
                stream_event=stream_event_payload(
                    ErrorStreamEvent(
                        message=str(latest.get("message") or "Unknown error"),
                        error_type=str(latest.get("type") or latest.get("error_type") or "RuntimeError"),
                        recoverable=bool(latest.get("recoverable", True)),
                    )
                ),
            ),
            event("final_response", content=final),
        ],
    })

