"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models.base import dump_model, validate_list
from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.tools import ToolCall, ToolResult, tool_result_to_tool_message


def tool_router_node(state: dict, deps: AppDependencies) -> dict:
    """Route the next pending tool call to execution, permission, skill, agent, MCP, or recovery.

    This node only classifies and prepares state. It does not execute tools; side effects remain
    behind `permission_gate` and `tool_executor`.
    """

    calls = validate_list(ToolCall, state.get("pending_tool_calls", []))
    metadata = dict(state.get("metadata", {}))
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
            "ui_events": [event("tool_call_error", id=call.id, name=name, status="rejected", reason="disallowed_by_skill")],
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
    if tool.runtime.route == "mcp_graph":
        metadata["tool_route"] = "mcp_tool"
        return merge_updates(pre_tool_update, {"metadata": metadata})
    decision = deps.permission_service.decide(tool, current, call.args)
    if decision.decision == "ask":
        metadata["tool_route"] = "needs_permission"
        pending = dump_model(deps.permission_service.confirmation_payload(call, tool, decision.reason))
        update = {
            "metadata": metadata,
            "pending_confirmation": pending,
            "ui_events": [event("permission_required", **pending)],
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
        return merge_updates(pre_tool_update, {
            "metadata": metadata,
            "tool_results": [result_payload],
            "messages": [tool_result_to_tool_message(result)],
            "pending_tool_calls": [],
        })
    metadata["tool_route"] = "execute"
    return merge_updates(pre_tool_update, {"metadata": metadata})
