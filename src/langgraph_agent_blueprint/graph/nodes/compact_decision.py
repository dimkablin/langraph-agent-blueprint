"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models import event


def compact_decision_node(state: dict, deps: AppDependencies) -> dict:
    """Decide whether the turn should enter the compaction path and record the route flag."""

    metadata = dict(state.get("metadata", {}))
    decision = deps.compaction_service.compaction_decision(state)
    metadata["compact_route"] = "compact" if decision.should_compact else "skip"
    metadata["compact_after_route"] = "persist_session" if metadata.get("compact_requested") else "model_call"
    if not decision.should_compact:
        return {"metadata": metadata, "ui_events": [event("node_finished", node="compact_decision")]}
    return {
        "metadata": metadata,
        "ui_events": [
            event(
                "compact_started",
                node="compact_decision",
                reason=decision.reason,
                message_count=decision.message_count,
                estimated_tokens=decision.estimated_tokens,
            )
        ],
    }

