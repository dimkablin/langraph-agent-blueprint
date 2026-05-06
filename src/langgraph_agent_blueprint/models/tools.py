"""Pydantic tool-call and tool-result envelopes for provider/tool boundaries."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import ToolMessage
from pydantic import Field

from langgraph_agent_blueprint.utils.ids import new_id

from .base import FrozenRuntimeModel


ToolCallStatus = Literal["pending", "approved", "rejected", "running", "finished", "error"]
ToolResultStatus = Literal["ok", "error", "rejected", "disabled", "unavailable"]


class ToolCall(FrozenRuntimeModel):
    """Normalized model-callable tool request proposed by a provider or command."""

    id: str = Field(default_factory=lambda: new_id("tool"))
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    provider: str = "unknown"
    raw: Any | None = None
    status: ToolCallStatus = "pending"


class ToolResult(FrozenRuntimeModel):
    """Structured result envelope returned by tool execution or policy rejection."""

    id: str
    name: str
    status: ToolResultStatus
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    state_update: dict[str, Any] = Field(default_factory=dict)
    output_ref: str | None = None
    error: dict[str, Any] | str | None = None

    @property
    def tool_call_id(self) -> str:
        return self.id

    @property
    def tool_name(self) -> str:
        return self.name


def normalize_provider_tool_call(raw: Any, provider: str = "unknown") -> ToolCall:
    """Normalize a raw provider-specific tool-call object into a ToolCall DTO."""

    if not isinstance(raw, dict):
        raise TypeError("provider tool call must be a mapping")
    function = raw.get("function") if isinstance(raw.get("function"), dict) else {}
    name = raw.get("name") or function.get("name")
    args = raw.get("args")
    if args is None:
        args = raw.get("arguments") or function.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"value": args}
    return ToolCall(
        id=str(raw.get("id") or new_id("tool")),
        name=str(name or ""),
        args=args if isinstance(args, dict) else {},
        provider=provider,
        raw=raw,
        status=raw.get("status", "pending"),
    )


def normalize_provider_tool_calls(raw_calls: list[Any], provider: str = "unknown") -> list[ToolCall]:
    """Normalize a list of raw provider tool calls, dropping entries that fail validation."""

    calls: list[ToolCall] = []
    for raw in raw_calls:
        try:
            call = normalize_provider_tool_call(raw, provider)
        except (TypeError, ValueError):
            continue
        if call.name:
            calls.append(call)
    return calls


def tool_result_to_tool_message(result: ToolResult) -> ToolMessage:
    """Convert a typed ToolResult into a provider-compatible ToolMessage."""

    payload = {
        "name": result.name,
        "status": result.status,
        "content": result.content,
        "metadata": result.metadata,
    }
    if result.error is not None:
        payload["error"] = result.error
    return ToolMessage(content=json.dumps(payload, ensure_ascii=False), tool_call_id=result.id)
