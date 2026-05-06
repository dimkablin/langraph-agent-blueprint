"""Typed hook runtime boundary models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from .base import FrozenRuntimeModel


HookPoint = Literal[
    "session_start",
    "session_end",
    "user_prompt",
    "pre_context_build",
    "post_context_build",
    "pre_model",
    "post_model",
    "pre_tool",
    "post_tool",
    "permission_request",
    "permission_resolved",
    "pre_skill",
    "post_skill",
    "pre_compact",
    "post_compact",
    "error",
]

HookResultAction = Literal[
    "continue",
    "add_event",
    "add_system_context",
    "modify_context",
    "modify_metadata",
    "block",
    "request_permission",
    "error",
]

HookRuntimeKind = Literal["builtin", "declarative"]
HookSeverity = Literal["info", "warning", "error"]


class HookPolicy(FrozenRuntimeModel):
    """Policy envelope for hook execution and result handling."""

    allowed_actions: list[HookResultAction] = Field(
        default_factory=lambda: ["continue", "add_event", "add_system_context", "modify_metadata", "block"]
    )
    fail_open: bool = True
    allow_side_effects: bool = False


class HookRuntimeMetadata(FrozenRuntimeModel):
    """Data-only runtime metadata for declarative hooks."""

    kind: HookRuntimeKind = "declarative"
    action: HookResultAction = "continue"
    content: str | None = None
    event_type: str | None = None
    event_data: dict[str, Any] = Field(default_factory=dict)
    metadata_update: dict[str, Any] = Field(default_factory=dict)
    context_update: dict[str, Any] = Field(default_factory=dict)
    block_reason: str | None = None


class HookContribution(FrozenRuntimeModel):
    """Registered hook capability contributed by core runtime or a plugin."""

    id: str
    plugin_name: str | None = None
    hook_point: HookPoint
    description: str | None = None
    enabled: bool = True
    priority: int = 100
    trusted: bool = False
    source_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    policy: HookPolicy = Field(default_factory=HookPolicy)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("hook id must not be empty")
        if any(part in value for part in ("..", "/", "\\")):
            raise ValueError("hook id must not contain path traversal characters")
        return value


class HookContext(FrozenRuntimeModel):
    """Runtime context passed to hook handlers without exposing mutable graph state."""

    session_id: str
    thread_id: str | None = None
    project_root: str | None = None
    cwd: str | None = None
    hook_point: HookPoint
    input_text: str | None = None
    active_tool: dict[str, Any] | None = None
    active_skill: dict[str, Any] | None = None
    active_command: dict[str, Any] | None = None
    permission_request: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HookInvocation(FrozenRuntimeModel):
    """One typed hook invocation."""

    hook: HookContribution
    context: HookContext


class HookResult(FrozenRuntimeModel):
    """Controlled hook output consumed by graph nodes."""

    hook_id: str
    hook_point: HookPoint
    action: HookResultAction = "continue"
    data: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None
    severity: HookSeverity = "info"


class HookRunSummary(FrozenRuntimeModel):
    """Summary returned by HookService for one hook point."""

    hook_point: HookPoint
    results: list[HookResult] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)

