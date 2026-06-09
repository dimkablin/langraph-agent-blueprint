"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.graph.run_control import cancellation_update
from langgraph_agent_blueprint.models import (
    AgentActivityEvent,
    AgentActivitySource,
    PermissionStateStreamEvent,
    StreamError,
    ToolCall,
    ToolLifecycleStreamEvent,
    ToolResult,
    dump_model,
    event,
    stream_event_payload,
    tool_result_to_tool_message,
    validate_list,
)
from langgraph_agent_blueprint.services.permission_service import DEFAULT_SENSITIVE_ARG_KEYS, summarize_args
from langgraph_agent_blueprint.utils.activity import safe_activity_data


def tool_router_node(state: dict, deps: AppDependencies) -> dict:
    """Route the next pending tool call to execution, permission, skill, agent, MCP, or recovery.

    This node only classifies and prepares state. It does not execute tools; side effects remain
    behind `permission_gate` and `tool_executor`.
    """

    calls = validate_list(ToolCall, state.get("pending_tool_calls", []))
    metadata = dict(state.get("metadata", {}))
    if metadata.get("runtime_cancelled"):
        metadata["tool_route"] = "cancelled"
        return {"metadata": metadata}
    cancelled = cancellation_update(state, deps, node="tool_router")
    if cancelled is not None:
        metadata = {**cancelled.get("metadata", {}), "tool_route": "cancelled"}
        return {**cancelled, "metadata": metadata}
    if not calls:
        metadata["tool_route"] = "no_tools"
        return {"metadata": metadata}
    call = calls[0]
    name = call.name
    pre_tool_update = run_hook_point(deps, state, "pre_tool", active_tool=call.model_dump(mode="json"))
    if hook_blocked(pre_tool_update):
        blocked_metadata = {**pre_tool_update.get("metadata", {}), "tool_route": "rejected"}
        reason = pre_tool_update.get("final_response") or "Tool call blocked by hook."
        result = ToolResult(id=call.id, name=name, status="rejected", content=str(reason), metadata={"reason": "blocked_by_hook"})
        result_payload = dump_model(result)
        return merge_updates(
            pre_tool_update,
            {
                "metadata": blocked_metadata,
                "tool_results": [result_payload],
                "messages": [tool_result_to_tool_message(result)],
                "pending_tool_calls": [],
            },
        )
    current = state_with_update(state, pre_tool_update)
    metadata = dict(current.get("metadata", {}))
    allowed_tools = metadata.get("allowed_tools_override")
    if allowed_tools and name not in set(allowed_tools):
        metadata["tool_route"] = "rejected"
        result = ToolResult(
            id=call.id,
            name=name,
            status="rejected",
            content=f"Tool {name} is not allowed in the active skill scope.",
            metadata={"reason": "disallowed_by_skill"},
        )
        result_payload = dump_model(result)
        return merge_updates(pre_tool_update, {
            "metadata": metadata,
            "tool_results": [result_payload],
            "messages": [tool_result_to_tool_message(result)],
            "pending_tool_calls": [],
            "ui_events": [
                event(
                    "tool_call_error",
                    id=call.id,
                    name=name,
                    status="rejected",
                    reason="disallowed_by_skill",
                    stream_event=stream_event_payload(
                        ToolLifecycleStreamEvent(
                            phase="blocked",
                            tool_call_id=call.id,
                            tool_name=name,
                            title=f"{name} blocked",
                            result_summary="Tool is not allowed in the active skill scope.",
                            error=StreamError(type="ToolNotAllowed", message="Tool is not allowed in the active skill scope."),
                            details={"reason": "disallowed_by_skill"},
                        )
                    ),
                )
            ],
        })
    try:
        tool = deps.tool_registry.get(name)
    except KeyError as exc:
        metadata["tool_route"] = "error"
        return merge_updates(pre_tool_update, {
            "metadata": metadata,
            "errors": [{"message": str(exc), "type": "UnknownTool", "recoverable": True}],
        })
    if tool.runtime.route == "skill_graph":
        metadata["tool_route"] = "skill_tool"
        return merge_updates(pre_tool_update, {
            "metadata": metadata,
            "active_skill": {
                "name": call.args.get("skill"),
                "args": call.args.get("args", ""),
                "tool_call_id": call.id,
            },
        })
    if tool.runtime.route == "agent_graph":
        metadata["tool_route"] = "agent_tool"
        return merge_updates(pre_tool_update, {"metadata": metadata})
    decision = deps.permission_service.decide(tool, current, call.args)
    execution_route = "mcp_tool" if tool.runtime.route == "mcp_graph" else "execute"
    if decision.decision == "ask":
        metadata["tool_route"] = "needs_permission"
        metadata["after_permission_route"] = execution_route
        pending = dump_model(deps.permission_service.confirmation_payload(call, tool, decision.reason))
        permission_event = event(
            "permission_required",
            **pending,
            stream_event=stream_event_payload(_permission_state_stream_event(status="required", payload=pending, reason=decision.reason)),
            activity=_permission_activity(
                call=call,
                tool=tool,
                reason=decision.reason,
                activity_type="permission.tool.requested",
                status="pending",
                title="Permission required",
                data=pending,
            ).model_dump(mode="json"),
        )
        writer = _stream_writer(current)
        if writer is not None:
            writer(permission_event)
        update = {
            "metadata": metadata,
            "pending_confirmation": pending,
            "ui_events": [permission_event],
        }
        permission_hook_update = run_hook_point(
            deps,
            state_with_update(current, update),
            "permission_request",
            active_tool=call.model_dump(mode="json"),
            permission_request=pending,
        )
        return merge_updates(pre_tool_update, update, permission_hook_update)
    if decision.decision == "deny":
        metadata["tool_route"] = "rejected"
        result = ToolResult(id=call.id, name=name, status="rejected", content=decision.reason)
        result_payload = dump_model(result)
        denied_data = _permission_activity_data(call, tool, decision.reason)
        return merge_updates(pre_tool_update, {
            "metadata": metadata,
            "tool_results": [result_payload],
            "messages": [tool_result_to_tool_message(result)],
            "pending_tool_calls": [],
            "ui_events": [
                event(
                    "permission_resolved",
                    tool_call_id=call.id,
                    tool_name=name,
                    approved=False,
                    decision="rejected",
                    reason=decision.reason,
                    stream_event=stream_event_payload(
                        _permission_state_stream_event(status="blocked", payload=denied_data, reason=decision.reason)
                    ),
                    activity=_permission_activity(
                        call=call,
                        tool=tool,
                        reason=decision.reason,
                        activity_type="permission.tool.denied",
                        status="blocked",
                        title="Permission denied",
                        data=denied_data,
                    ).model_dump(mode="json"),
                )
            ],
        })
    metadata["tool_route"] = execution_route
    metadata.pop("after_permission_route", None)
    return merge_updates(pre_tool_update, {"metadata": metadata})


def _permission_activity(
    *,
    call: ToolCall,
    tool: object,
    reason: str,
    activity_type: str,
    status: str,
    title: str,
    data: dict,
) -> AgentActivityEvent:
    return AgentActivityEvent(
        id=f"activity_{call.id}_{activity_type.rsplit('.', 1)[-1]}",
        type=activity_type,
        source=AgentActivitySource(kind="permission", name=call.name, component="PermissionService"),
        category="permission",
        status=status,  # type: ignore[arg-type]
        title=title,
        summary=str(reason),
        data=safe_activity_data(data),
    )


def _permission_activity_data(call: ToolCall, tool: object, reason: str) -> dict:
    permission = getattr(tool, "permission", None)
    sensitive_keys = DEFAULT_SENSITIVE_ARG_KEYS | set(getattr(permission, "sensitive_arg_keys", set()) or set())
    return {
        "tool_call_id": call.id,
        "tool_name": call.name,
        "action": getattr(permission, "action", None),
        "risk": getattr(permission, "risk", None),
        "args_summary": summarize_args(call.args, sensitive_keys=sensitive_keys),
        "reason": reason,
    }


def _permission_state_stream_event(*, status: str, payload: dict, reason: str) -> PermissionStateStreamEvent:
    return PermissionStateStreamEvent(
        status=status,  # type: ignore[arg-type]
        tool_call_id=str(payload.get("tool_call_id") or ""),
        tool_name=str(payload.get("tool_name") or ""),
        action=_optional_str(payload.get("action")),
        risk=_optional_str(payload.get("risk")),
        args_summary=_optional_str(payload.get("args_summary")),
        reason=reason or _optional_str(payload.get("reason")),
        args=payload.get("args") if isinstance(payload.get("args"), dict) else {},
    )


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _stream_writer(state: dict) -> object | None:
    if not state.get("metadata", {}).get("streaming_enabled"):
        return None
    try:
        return get_stream_writer()
    except RuntimeError:
        return None
