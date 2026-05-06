"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.state import AssistantState
from langgraph_agent_blueprint.models.messages import event


def _memory_node(state: dict, deps: AppDependencies) -> dict:
    memory = deps.memory_service.load_memory(state.get("project_root"), state.get("session_id"))
    return {"memory": memory, "ui_events": [event("memory_updated", scopes=list(memory))]}


def build_memory_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("memory_load", lambda state: _memory_node(state, deps))
    graph.add_edge(START, "memory_load")
    graph.add_edge("memory_load", END)
    return graph

