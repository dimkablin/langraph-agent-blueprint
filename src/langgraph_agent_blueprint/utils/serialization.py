"""Serialization helpers for converting LangChain messages to and from persisted JSON records."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage


def message_to_dict(message: BaseMessage) -> dict[str, Any]:
    """Serialize a LangChain message for JSONL session storage."""

    role = "base"
    if isinstance(message, HumanMessage):
        role = "human"
    elif isinstance(message, AIMessage):
        role = "ai"
    elif isinstance(message, SystemMessage):
        role = "system"
    elif isinstance(message, ToolMessage):
        role = "tool"
    data = {"role": role, "content": getattr(message, "content", ""), "type": message.__class__.__name__}
    if isinstance(message, AIMessage):
        data["tool_calls"] = getattr(message, "tool_calls", []) or []
    if isinstance(message, ToolMessage):
        data["tool_call_id"] = getattr(message, "tool_call_id", "")
    return data


def message_from_dict(data: dict[str, Any]) -> BaseMessage:
    """Deserialize a stored message."""

    role = data.get("role")
    content = data.get("content", "")
    if role == "human":
        return HumanMessage(content=content)
    if role == "ai":
        return AIMessage(content=content, tool_calls=data.get("tool_calls", []))
    if role == "system":
        return SystemMessage(content=content)
    if role == "tool":
        return ToolMessage(content=content, tool_call_id=data.get("tool_call_id", "stored"))
    return HumanMessage(content=content)
