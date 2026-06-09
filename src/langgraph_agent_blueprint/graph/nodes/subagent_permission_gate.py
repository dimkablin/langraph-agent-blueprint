"""Parent-owned approval gate for interrupted subagent child graph runs."""

from __future__ import annotations

from langgraph.types import interrupt

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.subgraphs.agent_graph import resume_pending_subagent_approval


def subagent_permission_gate_node(state: dict, deps: AppDependencies) -> dict:
    """Interrupt the parent graph for a child permission request, then resume the child."""

    pending = state.get("pending_subagent_approval")
    if not isinstance(pending, dict):
        return {}
    request = pending.get("permission_request", {})
    decision = interrupt(request)
    return resume_pending_subagent_approval(state, deps, decision)
