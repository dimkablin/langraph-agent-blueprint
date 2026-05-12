"""Pydantic metadata contracts for tool permissions, routing, and state effects."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from langgraph_agent_blueprint.models.base import FrozenRuntimeModel
from langgraph_agent_blueprint.models.permissions import PermissionAction, PermissionRisk


ToolKind = Literal[
    "file",
    "search",
    "shell",
    "network",
    "notebook",
    "todo",
    "skill",
    "agent",
    "diagnostics",
    "mcp",
    "plugin",
    "custom",
]
ToolRoute = Literal["execute", "skill_graph", "agent_graph", "mcp_graph"]
ToolStateEffectKind = Literal[
    "record_file_read",
    "record_file_write",
    "record_file_edit",
    "replace_todos",
    "append_child_run",
]


class ToolPermissionMetadata(FrozenRuntimeModel):
    """Permission and risk metadata declared by a model-callable tool."""

    action: PermissionAction
    risk: PermissionRisk
    is_read_only: bool = False
    requires_permission: bool = False
    reason: str | None = None
    allowed_in_plan_mode: bool = False
    requires_network: bool = False
    external: bool = False
    sensitive_arg_keys: set[str] = Field(default_factory=set)


class ToolRuntimeMetadata(FrozenRuntimeModel):
    """Runtime metadata used by LangGraph routing and post-execution state effects."""

    kind: ToolKind = "custom"
    route: ToolRoute = "execute"
    state_effects: list[ToolStateEffectKind] = Field(default_factory=list)
    supports_streaming: bool = False
    returns_large_output: bool = False
    can_run_in_skill: bool = True
    can_run_in_headless: bool = True


class ToolActivitySpec(FrozenRuntimeModel):
    """Producer-owned activity metadata exposed by model-callable tools."""

    category: str = "tool"
    display_name: str
    started_type: str
    completed_type: str
    failed_type: str
    blocked_type: str | None = None
    icon: str | None = None


class ToolStateEffect(FrozenRuntimeModel):
    """Typed state effect returned by a tool after successful execution."""

    kind: ToolStateEffectKind
    data: dict[str, Any] = Field(default_factory=dict)
