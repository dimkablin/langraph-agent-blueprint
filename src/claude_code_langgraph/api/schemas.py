from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    thread_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    thread_id: str
    final_response: str | None = None
    events: list[dict[str, Any]]
    permission_required: dict[str, Any] | None = None


class ApprovalRequest(BaseModel):
    thread_id: str
    decision: dict[str, Any]
