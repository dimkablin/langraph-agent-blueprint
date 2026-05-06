"""Central permission policy service for read, write, shell, network, MCP, plugin, and plan-mode decisions."""

from __future__ import annotations

from typing import Any

from claude_code_langgraph.config import PermissionMode
from claude_code_langgraph.models.base import dump_model
from claude_code_langgraph.models.permissions import PermissionCheck, PermissionRequest


class PermissionService:
    """Permission policy for tool side effects and human-in-the-loop approvals."""

    def __init__(self, mode: PermissionMode = "default") -> None:
        self.mode = mode

    def decide(self, tool: Any, state: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        """Return allow/ask/deny for a tool call under the active permission mode and plan state."""

        if state.get("plan_mode", {}).get("enabled") and not getattr(tool, "is_read_only", False):
            return dump_model(PermissionCheck(decision="ask", reason="plan mode blocks side effects until approval"))
        if self.mode == "strict" and getattr(tool, "requires_permission", False):
            return dump_model(PermissionCheck(decision="ask", reason="strict mode requires approval"))
        if self.mode == "accept_edits" and getattr(tool, "safety", "") == "write":
            return dump_model(PermissionCheck(decision="allow", reason="accept_edits allows file edits"))
        if getattr(tool, "requires_permission", False):
            return dump_model(PermissionCheck(decision="ask", reason=f"{tool.name} requires approval"))
        if getattr(tool, "is_read_only", False) and self.mode in {"default", "bypass_read_only", "accept_edits"}:
            return dump_model(PermissionCheck(decision="allow", reason="read-only tool allowed"))
        return dump_model(PermissionCheck(decision="allow", reason="tool allowed by policy"))

    @staticmethod
    def confirmation_payload(tool_call: dict[str, Any], reason: str) -> dict[str, Any]:
        request = PermissionRequest(
            tool_name=str(tool_call["name"]),
            tool_call_id=str(tool_call["id"]),
            action=_permission_action(str(tool_call["name"])),
            args_summary=_args_summary(tool_call.get("args", {})),
            risk=_permission_risk(str(tool_call["name"])),
            args=tool_call.get("args", {}) if isinstance(tool_call.get("args", {}), dict) else {},
            reason=reason,
        )
        return dump_model(request)


def _permission_action(tool_name: str) -> str:
    if tool_name in {"write_file"}:
        return "write"
    if tool_name in {"edit_file", "notebook_edit"}:
        return "edit"
    if tool_name in {"bash", "powershell"}:
        return "shell"
    if tool_name in {"web_fetch", "web_search"}:
        return "network"
    if tool_name in {"memory", "remember"}:
        return "memory"
    return "unknown"


def _permission_risk(tool_name: str) -> str:
    if tool_name in {"bash", "powershell"}:
        return "high"
    if tool_name in {"write_file", "edit_file", "notebook_edit", "web_fetch", "web_search"}:
        return "medium"
    return "low"


def _args_summary(args: Any) -> str:
    if not isinstance(args, dict) or not args:
        return "{}"
    rendered = ", ".join(f"{key}={value!r}" for key, value in sorted(args.items()))
    return rendered[:500]
