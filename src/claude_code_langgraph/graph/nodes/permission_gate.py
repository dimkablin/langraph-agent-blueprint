from __future__ import annotations

import json

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def permission_gate_node(state: dict, deps: AppDependencies) -> dict:
    pending = state.get("pending_confirmation")
    if not pending:
        return {}
    decision = interrupt(pending)
    approved = bool(decision.get("approved") if isinstance(decision, dict) else decision)
    record = {
        "tool_call_id": pending["tool_call_id"],
        "tool_name": pending["tool_name"],
        "approved": approved,
        "reason": decision.get("reason") if isinstance(decision, dict) else None,
    }
    metadata = dict(state.get("metadata", {}))
    if approved:
        metadata["tool_route"] = "execute"
        return {
            "metadata": metadata,
            "pending_confirmation": None,
            "permission_decisions": [record],
            "ui_events": [event("permission_resolved", **record)],
        }
    metadata["tool_route"] = "rejected"
    call = state.get("pending_tool_calls", [{}])[0]
    result = {"id": call.get("id"), "name": pending["tool_name"], "status": "rejected", "content": "Tool call rejected by user."}
    return {
        "metadata": metadata,
        "pending_confirmation": None,
        "permission_decisions": [record],
        "pending_tool_calls": [],
        "tool_results": [result],
        "messages": [
            ToolMessage(
                content=json.dumps(
                    {"name": result["name"], "status": result["status"], "content": result["content"]},
                    ensure_ascii=False,
                ),
                tool_call_id=str(result.get("id") or "unknown"),
            )
        ],
        "ui_events": [event("permission_resolved", **record)],
    }
