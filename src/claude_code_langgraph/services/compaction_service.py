from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage


class CompactionService:
    """Context accounting and compaction preserving active work."""

    def __init__(self, max_messages_before_compact: int = 30, keep_recent: int = 6) -> None:
        self.max_messages_before_compact = max_messages_before_compact
        self.keep_recent = keep_recent

    def estimate_tokens(self, messages: list[BaseMessage]) -> int:
        return sum(max(1, len(str(getattr(message, "content", ""))) // 4) for message in messages)

    def should_compact(self, state: dict[str, Any]) -> bool:
        if state.get("metadata", {}).get("compact_requested"):
            return True
        return len(state.get("messages", [])) > self.max_messages_before_compact

    def compact_state(self, state: dict[str, Any]) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        keep_count = min(self.keep_recent, max(1, len(messages) // 2))
        recent = messages[-keep_count:]
        old = messages[:-keep_count]
        summary = " | ".join(str(getattr(message, "content", "")) for message in old)
        summary_message = SystemMessage(content=f"Compacted prior context: {summary[:2000]}")
        return {
            "messages": [summary_message, *recent],
            "todos": list(state.get("todos", [])),
            "context_status": {
                **state.get("context_status", {}),
                "compacted": True,
                "summary": summary,
                "estimated_tokens": self.estimate_tokens(recent) + max(1, len(summary) // 4),
            },
        }
