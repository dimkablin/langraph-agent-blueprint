"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.graph.nodes.command_router import command_router_node
from claude_code_langgraph.graph.state import AssistantState


def build_command_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("command_router", lambda state: command_router_node(state, deps))
    graph.add_edge(START, "command_router")
    graph.add_edge("command_router", END)
    return graph

