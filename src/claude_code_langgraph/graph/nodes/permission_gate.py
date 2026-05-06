"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph.types import interrupt

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.base import dump_model
from claude_code_langgraph.models.messages import event
from claude_code_langgraph.models.tools import ToolCall, ToolResult, tool_result_to_tool_message


def permission_gate_node(state: dict, deps: AppDependencies) -> dict:
    """Interrupt for human approval and convert the resumed decision into graph updates.

    Approved calls proceed to execution; rejected calls append a structured ToolMessage so the
    model can explain the denial in the normal tool-result loop.
    """

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
    call = ToolCall.model_validate(state.get("pending_tool_calls", [{}])[0])
    result = ToolResult(id=call.id, name=pending["tool_name"], status="rejected", content="Tool call rejected by user.")
    result_payload = dump_model(result)
    return {
        "metadata": metadata,
        "pending_confirmation": None,
        "permission_decisions": [record],
        "pending_tool_calls": [],
        "tool_results": [result_payload],
        "messages": [tool_result_to_tool_message(result)],
        "ui_events": [event("permission_resolved", **record)],
    }
