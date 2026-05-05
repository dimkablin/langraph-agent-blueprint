"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def compact_context_node(state: dict, deps: AppDependencies) -> dict:
    """Replace older message history with a compact summary while preserving recent context."""

    update = deps.compaction_service.compact_state(state)
    update["messages"] = [RemoveMessage(id=REMOVE_ALL_MESSAGES), *update.get("messages", [])]
    update["final_response"] = "Context compacted."
    update["ui_events"] = [event("compact_finished", summary=update["context_status"].get("summary", "")[:200])]
    return update
