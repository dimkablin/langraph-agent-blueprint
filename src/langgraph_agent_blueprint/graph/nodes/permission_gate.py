"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph.types import interrupt

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models import (
    AgentActivityEvent,
    AgentActivitySource,
    PermissionDecision,
    PermissionRequest,
    ToolCall,
    ToolResult,
    dump_model,
    event,
    tool_result_to_tool_message,
)
from langgraph_agent_blueprint.utils.activity import safe_activity_data


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
        metadata["tool_route"] = metadata.pop("after_permission_route", "execute")
        update = {
            "metadata": metadata,
            "pending_confirmation": None,
            "permission_decisions": [record],
            "ui_events": [
                event(
                    "permission_resolved",
                    **record,
                    activity=_permission_resolution_activity(
                        request,
                        record,
                        activity_type="permission.tool.approved",
                        status="success",
                        title="Permission approved",
                    ).model_dump(mode="json"),
                )
            ],
        }
        hook_update = run_hook_point(
            deps,
            state_with_update(state, update),
            "permission_resolved",
            permission_request=request.model_dump(mode="json"),
            metadata={"permission_decision": record},
        )
        return merge_updates(update, hook_update)
    metadata["tool_route"] = "rejected"
    call = ToolCall.model_validate(state.get("pending_tool_calls", [{}])[0])
    result = ToolResult(id=call.id, name=request.tool_name, status="rejected", content="Tool call rejected by user.")
    result_payload = dump_model(result)
    update = {
        "metadata": metadata,
        "pending_confirmation": None,
        "permission_decisions": [record],
        "pending_tool_calls": [],
        "tool_results": [result_payload],
        "messages": [tool_result_to_tool_message(result)],
        "ui_events": [
            event(
                "permission_resolved",
                **record,
                activity=_permission_resolution_activity(
                    request,
                    record,
                    activity_type="permission.tool.denied",
                    status="blocked",
                    title="Permission denied",
                ).model_dump(mode="json"),
            )
        ],
    }
    hook_update = run_hook_point(
        deps,
        state_with_update(state, update),
        "permission_resolved",
        permission_request=request.model_dump(mode="json"),
        metadata={"permission_decision": record},
    )
    return merge_updates(update, hook_update)


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


def _permission_resolution_activity(
    request: PermissionRequest,
    record: dict,
    *,
    activity_type: str,
    status: str,
    title: str,
) -> AgentActivityEvent:
    reason = record.get("reason") or request.reason or title
    return AgentActivityEvent(
        id=f"activity_{request.tool_call_id}_{activity_type.rsplit('.', 1)[-1]}",
        type=activity_type,
        source=AgentActivitySource(kind="permission", name=request.tool_name, component="PermissionService"),
        category="permission",
        status=status,  # type: ignore[arg-type]
        title=title,
        summary=str(reason),
        data=safe_activity_data(
            {
                "tool_call_id": request.tool_call_id,
                "tool_name": request.tool_name,
                "action": request.action,
                "risk": request.risk,
                "args_summary": request.args_summary,
                "decision": record.get("decision"),
                "reason": reason,
            }
        ),
    )
