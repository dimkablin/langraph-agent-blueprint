"""Pydantic DTOs for FastAPI chat, approval, and response payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """API request payload for starting or continuing a graph-backed chat turn."""
    message: str
    session_id: str | None = None
    thread_id: str | None = None


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
