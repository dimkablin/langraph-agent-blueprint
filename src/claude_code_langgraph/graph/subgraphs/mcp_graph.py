"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.graph.nodes.tool_executor import tool_executor_node
from claude_code_langgraph.graph.state import AssistantState


def build_mcp_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("mcp_execute", lambda state: tool_executor_node(state, deps))
    graph.add_edge(START, "mcp_execute")
    graph.add_edge("mcp_execute", END)
    return graph

