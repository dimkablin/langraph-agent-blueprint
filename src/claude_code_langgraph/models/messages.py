from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    """Client-visible event emitted from graph nodes and adapters."""

    type: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
    """Return a serializable stream event dictionary."""

    return StreamEvent(type=event_type, data=data).model_dump(mode="json")

