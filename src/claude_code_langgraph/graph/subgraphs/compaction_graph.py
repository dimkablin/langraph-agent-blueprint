"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.graph.nodes.compact_context import compact_context_node
from claude_code_langgraph.graph.nodes.compact_decision import compact_decision_node
from claude_code_langgraph.graph.state import AssistantState


def build_compaction_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("compact_decision", lambda state: compact_decision_node(state, deps))
    graph.add_node("compact_context", lambda state: compact_context_node(state, deps))
    graph.add_edge(START, "compact_decision")
    graph.add_edge("compact_decision", "compact_context")
    graph.add_edge("compact_context", END)
    return graph

