"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.nodes.persist_session import persist_session_node
from langgraph_agent_blueprint.graph.state import AssistantState


def build_session_lifecycle_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("persist_session", lambda state: persist_session_node(state, deps))
    graph.add_edge(START, "persist_session")
    graph.add_edge("persist_session", END)
    return graph

