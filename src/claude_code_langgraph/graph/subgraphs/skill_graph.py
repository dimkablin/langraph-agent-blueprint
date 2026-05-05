"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.graph.nodes.skill_router import skill_router_node
from claude_code_langgraph.graph.state import AssistantState


def build_skill_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("skill_router", lambda state: skill_router_node(state, deps))
    graph.add_edge(START, "skill_router")
    graph.add_edge("skill_router", END)
    return graph

