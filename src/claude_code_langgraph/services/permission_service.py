"""Central permission policy service for read, write, shell, network, MCP, plugin, and plan-mode decisions."""

from __future__ import annotations

import json
from typing import Any

from claude_code_langgraph.config import PermissionMode
from claude_code_langgraph.models.permissions import PermissionCheck, PermissionRequest
from claude_code_langgraph.models.tools import ToolCall
from claude_code_langgraph.models.tool_metadata import ToolPermissionMetadata


DEFAULT_SENSITIVE_ARG_KEYS = {
    "api_key",
    "apikey",
    "token",
    "password",
    "secret",
    "authorization",
    "auth",
    "credential",
    "credentials",
}


class PermissionService:
    """Permission policy for tool side effects and human-in-the-loop approvals."""

    def __init__(self, mode: PermissionMode = "default") -> None:
        self.mode = mode

    def decide(self, tool: Any, state: dict[str, Any], args: dict[str, Any]) -> PermissionCheck:
        """Return allow/ask/deny for a tool call under the active permission mode and plan state."""

        permission = _tool_permission(tool)
        if state.get("plan_mode", {}).get("enabled") and not permission.is_read_only and not permission.allowed_in_plan_mode:
            return PermissionCheck(decision="ask", reason="plan mode blocks side effects until approval")
        if self.mode == "strict" and permission.requires_permission:
            return PermissionCheck(decision="ask", reason=permission.reason or "strict mode requires approval")
        if self.mode == "accept_edits" and permission.action in {"write", "edit"}:
            return PermissionCheck(decision="allow", reason="accept_edits allows file edits")
        if permission.requires_permission:
            return PermissionCheck(decision="ask", reason=permission.reason or f"{getattr(tool, 'name', 'tool')} requires approval")
        if permission.is_read_only and self.mode in {"default", "bypass_read_only", "accept_edits"}:
            return PermissionCheck(decision="allow", reason="read-only tool allowed")
        return PermissionCheck(decision="allow", reason="tool allowed by policy")

    @staticmethod
    def confirmation_payload(tool_call: ToolCall | dict[str, Any], tool: Any, reason: str) -> PermissionRequest:
        call = ToolCall.model_validate(tool_call)
        permission = _tool_permission(tool)
        sensitive_keys = DEFAULT_SENSITIVE_ARG_KEYS | set(permission.sensitive_arg_keys)
        request = PermissionRequest(
            tool_name=call.name,
            tool_call_id=call.id,
            action=permission.action,
            args_summary=summarize_args(call.args, sensitive_keys=sensitive_keys),
            risk=permission.risk,
            args=redact_args(call.args, sensitive_keys),
            reason=reason,
        )
        return request


def redact_args(args: dict[str, Any], sensitive_keys: set[str]) -> dict[str, Any]:
    """Return args with sensitive keys recursively replaced by redaction markers."""

    return _redact_value(args, {key.lower() for key in (DEFAULT_SENSITIVE_ARG_KEYS | sensitive_keys)})


def summarize_args(args: dict[str, Any], *, sensitive_keys: set[str], limit: int = 500) -> str:
    """Render stable, redacted, truncated JSON for approval prompts and events."""

    if not args:
        return "{}"
    rendered = json.dumps(redact_args(args, sensitive_keys), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(rendered) <= limit:
        return rendered
    return rendered[: max(0, limit - 13)] + "...<truncated>"


def _tool_permission(tool: Any) -> ToolPermissionMetadata:
    permission = getattr(tool, "permission", None)
    if isinstance(permission, ToolPermissionMetadata):
        return permission
    return ToolPermissionMetadata(
        action="unknown",
        risk="high",
        requires_permission=True,
        external=True,
        reason="Unknown tool permission metadata requires approval.",
    )


def _redact_value(value: Any, sensitive_keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: ("***" if str(key).lower() in sensitive_keys else _redact_value(item, sensitive_keys)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, sensitive_keys) for item in value]
    return value
