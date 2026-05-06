"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.state import AssistantState
from langgraph_agent_blueprint.models.messages import event


def _agent_node(state: dict, deps: AppDependencies) -> dict:
    calls = state.get("pending_tool_calls", [])
    prompt = calls[0].get("args", {}).get("prompt", "") if calls else ""
    child = deps.agent_service.run_child(prompt, state)
    return {
        "child_runs": [child],
        "pending_tool_calls": [],
        "tool_results": [{"id": calls[0].get("id") if calls else "agent", "name": "agent", "status": "ok", "content": child["result"]}],
        "ui_events": [event("subagent_started", id=child["id"]), event("subagent_finished", id=child["id"], status="completed")],
    }


def build_agent_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("agent_run", lambda state: _agent_node(state, deps))
    graph.add_edge(START, "agent_run")
    graph.add_edge("agent_run", END)
    return graph

