"""Pydantic runtime event DTOs used by graph nodes, streaming, and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field

from langgraph_agent_blueprint.utils.ids import new_id

from .base import FrozenRuntimeModel


EventType = Literal[
    "session_started",
    "node_started",
    "node_finished",
    "command_started",
    "command_finished",
    "user_message",
    "model_token",
    "model_message",
    "usage_updated",
    "tool_call_started",
    "tool_call_finished",
    "tool_call_error",
    "permission_required",
    "permission_resolved",
    "skill_started",
    "skill_finished",
    "plugin_loaded",
    "plugin_skill_registered",
    "plugin_policy_applied",
    "plugin_policy_error",
    "superpowers_bootstrap_applied",
    "superpowers_skill_policy_applied",
    "mcp_server_starting",
    "mcp_server_connected",
    "mcp_server_failed",
    "mcp_tools_discovered",
    "mcp_resources_discovered",
    "mcp_prompts_discovered",
    "mcp_tool_call_started",
    "mcp_tool_call_finished",
    "mcp_tool_call_error",
    "context_resolution_started",
    "context_fragment_added",
    "context_resolution_error",
    "context_budget_applied",
    "model_context_prepared",
    "subagent_started",
    "subagent_finished",
    "subagent_error",
    "subagent_cancelled",
    "subagent_timeout",
    "subagent_event",
    "agent_activity",
    "hook_started",
    "hook_finished",
    "hook_blocked",
    "hook_event",
    "hook_error",
    "compact_started",
    "compact_finished",
    "memory_updated",
    "export_finished",
    "session_persisted",
    "runtime_metrics",
    "run_cancelled",
    "final_response",
    "error",
]
Severity = Literal["info", "warning", "error"]


class RuntimeEvent(FrozenRuntimeModel):
    """Client-visible runtime event emitted by graph nodes and adapters."""

    id: str = Field(default_factory=lambda: new_id("event"))
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str = "unknown"
    node: str | None = None
    severity: Severity = "info"
    data: dict[str, Any] = Field(default_factory=dict)


def make_event(
    event_type: EventType,
    session_id: str = "unknown",
    *,
    node: str | None = None,
    data: dict[str, Any] | None = None,
    severity: Severity = "info",
) -> RuntimeEvent:
    """Create a validated runtime event DTO."""

    payload = dict(data or {})
    return RuntimeEvent(type=event_type, session_id=session_id, node=node, severity=severity, data=payload)
