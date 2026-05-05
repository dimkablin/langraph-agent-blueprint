from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from .messages import Usage


class ModelRequest(BaseModel):
    """Provider-agnostic model request."""

    messages: list[Any] = Field(default_factory=list)
    system_context: str = ""
    tools: dict[str, dict[str, Any]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """Provider-agnostic model response."""

    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    raw: Any | None = None


def message_text(messages: list[BaseMessage]) -> str:
    """Return a compact text representation of messages for simple providers."""

    return "\n".join(str(getattr(message, "content", "")) for message in messages)

