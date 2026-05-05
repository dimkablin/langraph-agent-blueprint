from __future__ import annotations

from typing import Any

from claude_code_langgraph.config import PermissionMode


class PermissionService:
    """Permission policy for tool side effects and human-in-the-loop approvals."""

    def __init__(self, mode: PermissionMode = "default") -> None:
        self.mode = mode

    def decide(self, tool: Any, state: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        if state.get("plan_mode", {}).get("enabled") and not getattr(tool, "is_read_only", False):
            return {"decision": "ask", "reason": "plan mode blocks side effects until approval"}
        if self.mode == "strict" and getattr(tool, "requires_permission", False):
            return {"decision": "ask", "reason": "strict mode requires approval"}
        if self.mode == "accept_edits" and getattr(tool, "safety", "") == "write":
            return {"decision": "allow", "reason": "accept_edits allows file edits"}
        if getattr(tool, "requires_permission", False):
            return {"decision": "ask", "reason": f"{tool.name} requires approval"}
        if getattr(tool, "is_read_only", False) and self.mode in {"default", "bypass_read_only", "accept_edits"}:
            return {"decision": "allow", "reason": "read-only tool allowed"}
        return {"decision": "allow", "reason": "tool allowed by policy"}

    @staticmethod
    def confirmation_payload(tool_call: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "type": "permission_required",
            "tool_name": tool_call["name"],
            "tool_call_id": tool_call["id"],
            "args": tool_call.get("args", {}),
            "reason": reason,
        }
