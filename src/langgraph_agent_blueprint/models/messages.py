"""Runtime message, event, usage, tool-call, and tool-result DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models.base import dump_model
from langgraph_agent_blueprint.models.events import RuntimeEvent, make_event


class StreamEvent(RuntimeEvent):
    """Client-visible event emitted from graph nodes and adapters."""


class Usage(BaseModel):
    """Provider usage telemetry."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float | None = None
    model: str | None = None
    provider: str | None = None
    duration_ms: float | None = None
    tool_calls: int = 0


class ToolCallRecord(BaseModel):
    """Structured tool call proposed by a model or command."""

    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResultRecord(BaseModel):
    """Structured result from a tool execution attempt."""

    id: str
    name: str
    status: str
    content: str = ""
    output_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def event(event_type: str, **data: Any) -> dict[str, Any]:
    """Return a validated, serializable RuntimeEvent payload.

    This backward-compatible helper keeps call sites terse while ensuring every
    emitted event follows the typed boundary contract before it enters graph
    state, streaming, or session storage.
    """

    session_id = str(data.pop("session_id", "") or "unknown")
    node = data.pop("node", None)
    severity = data.pop("severity", "info") or "info"
    return dump_model(make_event(event_type, session_id, node=node, severity=severity, data=data))  # type: ignore[arg-type]
