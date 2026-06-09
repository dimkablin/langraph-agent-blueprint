"""Typed public stream-event payloads carried by RuntimeEvent.data['stream_event']."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter

from .base import FrozenRuntimeModel


StreamEventKind = Literal[
    "assistant_delta",
    "assistant_final",
    "progress",
    "tool_lifecycle",
    "permission_state",
    "subagent",
    "error",
    "artifact",
]
ToolLifecyclePhase = Literal["scheduled", "started", "completed", "failed", "blocked", "permission_required"]
PermissionStateStatus = Literal["required", "approved", "rejected", "blocked"]
SubagentPhase = Literal["started", "event", "finished", "error", "cancelled", "timeout"]


class AssistantDeltaStreamEvent(FrozenRuntimeModel):
    """One public assistant text delta for a visible assistant message."""

    kind: Literal["assistant_delta"] = "assistant_delta"
    message_id: str
    delta: str


class AssistantFinalStreamEvent(FrozenRuntimeModel):
    """Final visible assistant answer for a turn."""

    kind: Literal["assistant_final"] = "assistant_final"
    message_id: str
    content: str


class ProgressStreamEvent(FrozenRuntimeModel):
    """Concise public progress narration, not hidden reasoning."""

    kind: Literal["progress"] = "progress"
    message: str
    stage: str | None = None
    message_id: str | None = None


class StreamError(FrozenRuntimeModel):
    """Normalized public error summary."""

    type: str
    message: str


class ToolLifecycleStreamEvent(FrozenRuntimeModel):
    """One lifecycle transition for a model-requested tool call."""

    kind: Literal["tool_lifecycle"] = "tool_lifecycle"
    phase: ToolLifecyclePhase
    tool_call_id: str
    tool_name: str
    title: str | None = None
    args_summary: str | None = None
    result_summary: str | None = None
    command: str | None = None
    path: str | None = None
    exit_code: int | None = None
    duration_ms: float | None = None
    error: StreamError | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class PermissionStateStreamEvent(FrozenRuntimeModel):
    """Human-in-the-loop or policy state for one tool call."""

    kind: Literal["permission_state"] = "permission_state"
    status: PermissionStateStatus
    tool_call_id: str
    tool_name: str
    action: str | None = None
    risk: str | None = None
    args_summary: str | None = None
    reason: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    scope: Literal["tool", "subagent"] = "tool"
    parent_session_id: str | None = None
    parent_thread_id: str | None = None
    child_session_id: str | None = None
    child_thread_id: str | None = None
    child_run_id: str | None = None
    subagent_name: str | None = None


class SubagentStreamEvent(FrozenRuntimeModel):
    """Typed parent-stream envelope for one subagent lifecycle or child event."""

    kind: Literal["subagent"] = "subagent"
    phase: SubagentPhase
    subagent_id: str
    run_id: str
    sequence: int
    parent_session_id: str | None = None
    parent_thread_id: str | None = None
    child_session_id: str | None = None
    child_thread_id: str | None = None
    agent_call_id: str | None = None
    name: str | None = None
    purpose: str | None = None
    status: str | None = None
    summary: str | None = None
    child_event_id: str | None = None
    child_event_type: str | None = None
    child_event: dict[str, Any] = Field(default_factory=dict)
    child_stream_event: dict[str, Any] = Field(default_factory=dict)
    error: StreamError | None = None


class ErrorStreamEvent(FrozenRuntimeModel):
    """Runtime error event rendered from typed data rather than event-name heuristics."""

    kind: Literal["error"] = "error"
    message: str
    error_type: str | None = None
    recoverable: bool | None = None


class ArtifactStreamEvent(FrozenRuntimeModel):
    """Artifact reference created during a runtime turn."""

    kind: Literal["artifact"] = "artifact"
    artifact_id: str
    artifact_kind: str
    uri: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


RuntimeStreamEvent = Annotated[
    AssistantDeltaStreamEvent
    | AssistantFinalStreamEvent
    | ProgressStreamEvent
    | ToolLifecycleStreamEvent
    | PermissionStateStreamEvent
    | SubagentStreamEvent
    | ErrorStreamEvent
    | ArtifactStreamEvent,
    Field(discriminator="kind"),
]

_RUNTIME_STREAM_EVENT_ADAPTER = TypeAdapter(RuntimeStreamEvent)


def stream_event_payload(payload: RuntimeStreamEvent | dict[str, Any]) -> dict[str, Any]:
    """Validate and dump a public stream-event payload."""

    return _RUNTIME_STREAM_EVENT_ADAPTER.validate_python(payload).model_dump(mode="json", exclude_none=True)
