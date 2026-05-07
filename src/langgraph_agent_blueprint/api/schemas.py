"""Pydantic DTOs for FastAPI chat, approval, and response payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator

from langgraph_agent_blueprint.utils.ids import validate_session_id, validate_thread_id


class ChatRequest(BaseModel):
    """API request payload for starting or continuing a graph-backed chat turn."""
    message: str
    session_id: str | None = None
    thread_id: str | None = None

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str | None) -> str | None:
        return validate_session_id(value) if value is not None else None

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, value: str | None) -> str | None:
        return validate_thread_id(value) if value is not None else None


class ChatResponse(BaseModel):
    """API response payload containing session ids, final text, events, and pending approvals."""
    session_id: str
    thread_id: str
    final_response: str | None = None
    events: list[dict[str, Any]]
    permission_required: dict[str, Any] | None = None


class ApprovalRequest(BaseModel):
    """API request payload used to resume an interrupted graph with a human permission decision."""
    thread_id: str
    decision: dict[str, Any]

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, value: str) -> str:
        return validate_thread_id(value)
