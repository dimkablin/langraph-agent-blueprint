from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def tool_router_node(state: dict, deps: AppDependencies) -> dict:
    calls = list(state.get("pending_tool_calls", []))
    metadata = dict(state.get("metadata", {}))
    if not calls:
        metadata["tool_route"] = "no_tools"
        return {"metadata": metadata}
    call = calls[0]
    name = call["name"]
    if name in {"skill", "SkillTool"}:
        metadata["tool_route"] = "skill_tool"
        return {"metadata": metadata, "active_skill": {"name": call.get("args", {}).get("skill"), "args": call.get("args", {}).get("args", "")}}
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
        return {"metadata": metadata, "tool_results": [{"id": call["id"], "name": name, "status": "rejected", "content": decision["reason"]}], "pending_tool_calls": []}
    metadata["tool_route"] = "execute"
    return {"metadata": metadata}

