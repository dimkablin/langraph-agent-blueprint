"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph.types import interrupt

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models.base import dump_model
from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.permissions import PermissionDecision, PermissionRequest
from langgraph_agent_blueprint.models.tools import ToolCall, ToolResult, tool_result_to_tool_message


def permission_gate_node(state: dict, deps: AppDependencies) -> dict:
    """Interrupt for human approval and convert the resumed decision into graph updates.

    Approved calls proceed to execution; rejected calls append a structured ToolMessage so the
    model can explain the denial in the normal tool-result loop.
    """

    pending = state.get("pending_confirmation")
    if not pending:
        return {}
    request = PermissionRequest.model_validate(pending)
    decision = interrupt(pending)
    permission_decision = _resume_decision(request, decision)
    approved = permission_decision.decision == "approved"
    record = {
        "tool_call_id": request.tool_call_id,
        "tool_name": request.tool_name,
        "approved": approved,
        "decision": permission_decision.decision,
        "reason": permission_decision.reason,
        "remember": permission_decision.remember,
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
    result = ToolResult(id=call.id, name=request.tool_name, status="rejected", content="Tool call rejected by user.")
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


def _resume_decision(request: PermissionRequest, decision: object) -> PermissionDecision:
    """Validate LangGraph resume payloads while preserving the existing approved-bool shape."""

    if isinstance(decision, dict) and "decision" in decision:
        return PermissionDecision.model_validate({"tool_call_id": request.tool_call_id, **decision})
    if isinstance(decision, dict):
        approved = bool(decision.get("approved"))
        return PermissionDecision(
            tool_call_id=request.tool_call_id,
            decision="approved" if approved else "rejected",
            reason=decision.get("reason"),
            remember=bool(decision.get("remember", False)),
        )
    return PermissionDecision(tool_call_id=request.tool_call_id, decision="approved" if bool(decision) else "rejected")
