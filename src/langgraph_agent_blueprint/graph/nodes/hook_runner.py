"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies


def hook_runner_node(state: dict, deps: AppDependencies) -> dict:
    """Compatibility node retained for graph shape; lifecycle hooks run at owning nodes."""

    return {"hooks_state": {**state.get("hooks_state", {}), "post_turn_node_seen": True}}

