"""LangGraph subgraph module that packages a focused workflow for reuse by the main graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from claude_code_langgraph.graph.state import AssistantState
from claude_code_langgraph.models.messages import event


def _plan_todo_node(state: dict) -> dict:
    return {
        "plan_mode": {**state.get("plan_mode", {}), "enabled": True},
        "ui_events": [event("node_finished", node="plan_todo_graph")],
    }


def build_plan_todo_graph() -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("plan_todo", _plan_todo_node)
    graph.add_edge(START, "plan_todo")
    graph.add_edge("plan_todo", END)
    return graph

