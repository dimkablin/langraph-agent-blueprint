"""Pydantic contracts for human-in-the-loop permission requests and decisions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .base import FrozenRuntimeModel


PermissionAction = Literal[
    "read",
    "write",
    "edit",
    "shell",
    "network",
    "memory",
    "config",
    "todo",
    "skill",
    "agent",
    "diagnostics",
    "mcp",
    "plugin",
    "unknown",
]
PermissionRisk = Literal["low", "medium", "high"]
PermissionPolicy = Literal["allow", "ask", "deny"]


class PermissionCheck(FrozenRuntimeModel):
    """Typed policy check result before a tool is executed or interrupted."""

    decision: PermissionPolicy
    reason: str


class PermissionRequest(FrozenRuntimeModel):
    """Serialized approval request emitted through LangGraph interrupt state."""

    type: Literal["permission_required"] = "permission_required"
    tool_call_id: str
    tool_name: str
    action: PermissionAction
    args_summary: str
    risk: PermissionRisk
    reason: str
    args: dict[str, Any] = Field(default_factory=dict)


class PermissionDecision(FrozenRuntimeModel):
    """Validated resume payload for approval or rejection of a pending tool call."""

    tool_call_id: str
    decision: Literal["approved", "rejected"]
    reason: str | None = None
    remember: bool = False
