"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models import event


def compact_context_node(state: dict, deps: AppDependencies) -> dict:
    """Replace older message history with a compact summary while preserving recent context."""

    pre_update = run_hook_point(deps, state, "pre_compact")
    if hook_blocked(pre_update):
        return pre_update
    current = state_with_update(state, pre_update)
    before_message_count = len(current.get("messages", []))
    update = deps.compaction_service.compact_state(current)
    compacted_messages = update.get("messages", [])
    update["messages"] = [RemoveMessage(id=REMOVE_ALL_MESSAGES), *update.get("messages", [])]
    update["ui_events"] = [
        event(
            "compact_finished",
            summary=update["context_status"].get("summary", "")[:200],
            before_message_count=before_message_count,
            after_message_count=len(compacted_messages),
            estimated_tokens=update["context_status"].get("estimated_tokens"),
        )
    ]
    post_update = run_hook_point(deps, state_with_update(current, update), "post_compact")
    return merge_updates(pre_update, update, post_update)
