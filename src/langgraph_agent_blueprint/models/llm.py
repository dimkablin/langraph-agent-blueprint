"""Provider-agnostic model request and response DTOs used by graph model nodes."""

from __future__ import annotations

from typing import Any, Literal

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


class ModelStreamEvent(BaseModel):
    """One provider-agnostic model stream item."""

    type: Literal["token", "response"]
    token: str = ""
    response: ModelResponse | None = None


def message_text(messages: list[BaseMessage]) -> str:
    """Return a compact text representation of messages for simple providers."""

    return "\n".join(str(getattr(message, "content", "")) for message in messages)


def provider_tool_schemas(tools: object) -> list[dict[str, Any]]:
    """Return the provider-facing function-tool schema payload for context accounting."""

    if not isinstance(tools, dict):
        return []
    schemas: list[dict[str, Any]] = []
    for name, metadata in sorted(tools.items()):
        if not isinstance(metadata, dict):
            metadata = {}
        input_schema = metadata.get("input_schema") or {"type": "object", "properties": {}}
        if not isinstance(input_schema, dict):
            input_schema = {"type": "object", "properties": {}}
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": str(name),
                    "description": str(metadata.get("description") or ""),
                    "parameters": input_schema,
                },
            }
        )
    return schemas

