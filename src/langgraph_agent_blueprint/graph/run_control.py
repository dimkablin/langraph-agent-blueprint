"""Cooperative graph cancellation helpers shared by runtime nodes."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models import AgentActivityEvent, AgentActivitySource, event
from langgraph_agent_blueprint.services.run_control_service import DEFAULT_CANCELLATION_REASON


def cancellation_update(state: dict, deps: AppDependencies, *, node: str) -> dict | None:
    """Return a terminal state update when the active thread has been cancelled."""

    thread_id = str(state.get("thread_id") or "")
    if not deps.run_control_service.is_cancelled(thread_id):
        return None
    reason = deps.run_control_service.cancellation_reason(thread_id)
    final_response = DEFAULT_CANCELLATION_REASON
    metadata = {
        **state.get("metadata", {}),
        "runtime_cancelled": True,
        "compact_after_route": "persist_session",
    }
    activity = AgentActivityEvent(
        type="runtime.run.cancelled",
        source=AgentActivitySource(kind="runtime", component="AssistantGraphRuntime"),
        category="runtime",
        status="blocked",
        title="Run cancelled",
        summary=reason,
    )
    return {
        "metadata": metadata,
        "pending_tool_calls": [],
        "pending_confirmation": None,
        "final_response": final_response,
        "messages": [AIMessage(content=final_response)],
        "ui_events": [
            event(
                "run_cancelled",
                session_id=state.get("session_id") or "unknown",
                node=node,
                thread_id=thread_id,
                reason=reason,
                activity=activity.model_dump(mode="json"),
            )
        ],
    }
