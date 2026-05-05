"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.graph.nodes.hook_runner import hook_runner_node
from claude_code_langgraph.graph.nodes.permission_gate import permission_gate_node
from claude_code_langgraph.graph.nodes.tool_executor import tool_executor_node
from claude_code_langgraph.graph.state import AssistantState


def build_tool_execution_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("permission_gate", lambda state: permission_gate_node(state, deps))
    graph.add_node("tool_executor", lambda state: tool_executor_node(state, deps))
    graph.add_node("hook_runner", lambda state: hook_runner_node(state, deps))
    graph.add_edge(START, "permission_gate")
    graph.add_edge("permission_gate", "tool_executor")
    graph.add_edge("tool_executor", "hook_runner")
    graph.add_edge("hook_runner", END)
    return graph

