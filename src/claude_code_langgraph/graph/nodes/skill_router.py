from __future__ import annotations

from langchain_core.messages import HumanMessage

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def skill_router_node(state: dict, deps: AppDependencies) -> dict:
    active = state.get("active_skill")
    if not active:
        return {}
    result = deps.skill_service.invoke(active["name"], active.get("args", ""), state)
    metadata = {**state.get("metadata", {}), "allowed_tools_override": result.get("allowed_tools", [])}
    return {
        "active_skill": {"name": active["name"], "args": active.get("args", ""), "result": result},
        "messages": [HumanMessage(content=result["prompt"])],
        "metadata": metadata,
        "ui_events": [event("skill_started", name=active["name"]), event("skill_finished", name=active["name"])],
    }

