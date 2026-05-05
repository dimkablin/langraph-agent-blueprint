"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def normalize_input_node(state: dict, deps: AppDependencies) -> dict:
    if state.get("metadata", {}).get("input_normalized"):
        return {}
    metadata = {**state.get("metadata", {}), "input_normalized": True}
    attachments = list(state.get("attachments", []))
    message = HumanMessage(content=state.get("input_text", ""))
    return {
        "messages": [message],
        "attachments": attachments,
        "metadata": metadata,
        "ui_events": [event("node_finished", node="normalize_input")],
    }

