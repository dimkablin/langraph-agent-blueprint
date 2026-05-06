"""Utility module containing small reusable helpers used across the runtime."""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage


def message_role(message: BaseMessage) -> str:
    """Map a LangChain message instance to a transcript role."""

    if isinstance(message, HumanMessage):
        return "User"
    if isinstance(message, AIMessage):
        return "Assistant"
    if isinstance(message, SystemMessage):
        return "System"
    if isinstance(message, ToolMessage):
        return "Tool"
    return message.__class__.__name__


def render_messages(messages: list[BaseMessage]) -> str:
    """Render chat messages to plain text."""

    lines: list[str] = []
    for message in messages:
        content = getattr(message, "content", "")
        lines.append(f"{message_role(message)}: {content}")
    return "\n".join(lines)

