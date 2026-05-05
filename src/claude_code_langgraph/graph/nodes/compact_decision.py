"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def compact_decision_node(state: dict, deps: AppDependencies) -> dict:
    """Decide whether the turn should enter the compaction path and record the route flag."""

    metadata = dict(state.get("metadata", {}))
    should = deps.compaction_service.should_compact(state)
    metadata["compact_route"] = "compact" if should else "skip"
    return {"metadata": metadata, "ui_events": [event("compact_started" if should else "node_finished", node="compact_decision")]}

