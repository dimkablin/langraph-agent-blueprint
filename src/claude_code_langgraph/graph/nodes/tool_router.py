"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def tool_router_node(state: dict, deps: AppDependencies) -> dict:
    """Route the next pending tool call to execution, permission, skill, agent, MCP, or recovery.

    This node only classifies and prepares state. It does not execute tools; side effects remain
    behind `permission_gate` and `tool_executor`.
    """

    calls = list(state.get("pending_tool_calls", []))
    metadata = dict(state.get("metadata", {}))
    if not calls:
        metadata["tool_route"] = "no_tools"
        return {"metadata": metadata}
    call = calls[0]
    name = call["name"]
    allowed_tools = metadata.get("allowed_tools_override")
    if allowed_tools and name not in set(allowed_tools):
        metadata["tool_route"] = "rejected"
        result = {
            "id": call["id"],
            "name": name,
            "status": "rejected",
            "content": f"Tool {name} is not allowed in the active skill scope.",
            "metadata": {"reason": "disallowed_by_skill"},
        }
        return {
            "metadata": metadata,
            "tool_results": [result],
            "messages": [_tool_message(result)],
            "pending_tool_calls": [],
            "ui_events": [event("tool_call_error", id=call["id"], name=name, status="rejected", reason="disallowed_by_skill")],
        }
    if name in {"skill", "SkillTool"}:
        metadata["tool_route"] = "skill_tool"
        return {
            "metadata": metadata,
            "active_skill": {
                "name": call.get("args", {}).get("skill"),
                "args": call.get("args", {}).get("args", ""),
                "tool_call_id": call.get("id"),
            },
        }
    if name in {"agent", "task"}:
        metadata["tool_route"] = "agent_tool"
        return {"metadata": metadata}
    if name.startswith("mcp."):
        metadata["tool_route"] = "mcp_tool"
        return {"metadata": metadata}
    try:
        tool = deps.tool_registry.get(name)
    except KeyError as exc:
        metadata["tool_route"] = "error"
        return {
            "metadata": metadata,
            "errors": [{"message": str(exc), "type": "UnknownTool", "recoverable": True}],
        }
    decision = deps.permission_service.decide(tool, state, call.get("args", {}))
    if decision["decision"] == "ask":
        metadata["tool_route"] = "needs_permission"
        pending = deps.permission_service.confirmation_payload(call, decision["reason"])
        return {
            "metadata": metadata,
            "pending_confirmation": pending,
            "ui_events": [event("permission_required", **pending)],
        }
    if decision["decision"] == "deny":
        metadata["tool_route"] = "rejected"
        result = {"id": call["id"], "name": name, "status": "rejected", "content": decision["reason"]}
        return {
            "metadata": metadata,
            "tool_results": [result],
            "messages": [_tool_message(result)],
            "pending_tool_calls": [],
        }
    metadata["tool_route"] = "execute"
    return {"metadata": metadata}


def _tool_message(record: dict) -> ToolMessage:
    """Build a provider-compatible ToolMessage for rejected tool calls."""

    return ToolMessage(
        content=json.dumps(
            {"name": record.get("name"), "status": record.get("status"), "content": record.get("content", "")},
            ensure_ascii=False,
        ),
        tool_call_id=str(record.get("id") or "unknown"),
    )
