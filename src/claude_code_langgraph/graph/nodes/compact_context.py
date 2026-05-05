from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def compact_context_node(state: dict, deps: AppDependencies) -> dict:
    update = deps.compaction_service.compact_state(state)
    update["ui_events"] = [event("compact_finished", summary=update["context_status"].get("summary", "")[:200])]
    return update

