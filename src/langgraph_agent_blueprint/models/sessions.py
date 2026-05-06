"""Pydantic contracts for session metadata and storage snapshots."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import RuntimeModel


class SessionMetadata(RuntimeModel):
    """Validated session metadata boundary while preserving runtime-specific extras."""

    session_id: str
    project_root: str
    cwd: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "SessionMetadata":
        """Validate known metadata fields and place unknown flat fields into `extra`."""

        known = {"session_id", "project_root", "cwd", "provider", "model", "created_at", "updated_at", "usage"}
        payload = {key: value for key, value in record.items() if key in known}
        payload["extra"] = {key: value for key, value in record.items() if key not in known}
        return cls.model_validate(payload)

    def to_record(self) -> dict[str, Any]:
        """Return the historical flat metadata layout used by session storage."""

        data = self.model_dump(mode="json", exclude_none=True)
        extra = data.pop("extra", {})
        return {**data, **extra}


class SessionSnapshot(RuntimeModel):
    """Validated load boundary for a resumable session snapshot."""

    metadata: SessionMetadata
    messages: list[Any] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    todos: list[dict[str, Any]] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
