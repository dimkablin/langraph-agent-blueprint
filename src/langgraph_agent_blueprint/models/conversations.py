"""Typed contracts for durable multi-user conversation history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field, field_validator

from .base import RuntimeModel

ConversationStatus = Literal["active", "archived", "deleted"]
MessageRole = Literal["system", "user", "assistant", "tool"]


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp for storage records."""

    return datetime.now(timezone.utc).isoformat()


class ConversationCreate(RuntimeModel):
    """Service/API request for creating a user-owned conversation."""

    title: str | None = None
    project_id: str | None = None
    conversation_id: str | None = None
    thread_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def _clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned[:200] if cleaned else None


class ConversationRecord(RuntimeModel):
    """Persistent conversation/session/thread metadata owned by one user."""

    conversation_id: str
    user_id: str
    thread_id: str
    session_id: str
    project_id: str | None = None
    title: str | None = None
    status: ConversationStatus = "active"
    archived_at: str | None = None
    deleted_at: str | None = None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1


class ConversationListItem(RuntimeModel):
    """Lightweight list row for ChatGPT-style history sidebars."""

    conversation_id: str
    session_id: str
    thread_id: str
    title: str | None = None
    status: ConversationStatus = "active"
    project_id: str | None = None
    message_count: int = 0
    event_count: int = 0
    tool_call_count: int = 0
    artifact_count: int = 0
    created_at: str
    updated_at: str


class MessageCreate(RuntimeModel):
    """Message payload appended to a conversation turn."""

    role: MessageRole
    content: str
    message_id: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageRecord(RuntimeModel):
    """Normalized persisted chat message."""

    message_id: str
    conversation_id: str
    user_id: str
    role: MessageRole
    content: str
    order_index: int
    idempotency_key: str | None = None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamEventCreate(RuntimeModel):
    """Durable stream/progress event append payload."""

    event_id: str | None = None
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamEventRecord(RuntimeModel):
    """Normalized persisted stream/progress event."""

    event_id: str
    conversation_id: str
    user_id: str
    type: str
    order_index: int
    created_at: str
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallCreate(RuntimeModel):
    """Persistable tool call/result payload with redacted metadata."""

    tool_call_id: str | None = None
    name: str
    status: str = "completed"
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactCreate(RuntimeModel):
    """Persistable artifact reference for conversation history."""

    artifact_id: str | None = None
    kind: str
    uri: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationDetail(RuntimeModel):
    """Full conversation snapshot for read/resume/export flows."""

    conversation: ConversationRecord
    messages: list[MessageRecord] = Field(default_factory=list)
    events: list[StreamEventRecord] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


class StorageMetrics(RuntimeModel):
    """Minimal storage observability counters for persistence benchmarking."""

    read_count: int = 0
    write_count: int = 0
    last_read_latency_ms: float = 0.0
    last_write_latency_ms: float = 0.0
