"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import BaseMessage, SystemMessage


CompactionReason = Literal["manual", "token_threshold", "message_threshold"]


@dataclass(frozen=True)
class CompactionDecision:
    """Typed result of evaluating whether a state should be compacted."""

    should_compact: bool
    reason: CompactionReason | None
    message_count: int
    estimated_tokens: int


class CompactionService:
    """Context accounting and compaction preserving active work."""

    def __init__(
        self,
        max_tokens_before_compact: int = 12_000,
        keep_recent: int = 6,
        max_messages_before_compact: int | None = None,
    ) -> None:
        self.max_tokens_before_compact = max_tokens_before_compact
        self.keep_recent = keep_recent
        self.max_messages_before_compact = max_messages_before_compact

    def estimate_tokens(self, messages: list[BaseMessage]) -> int:
        return sum(max(1, len(str(getattr(message, "content", ""))) // 4) for message in messages)

    def compaction_decision(self, state: dict[str, Any]) -> CompactionDecision:
        """Return a typed compaction decision for the current runtime state."""

        messages = list(state.get("messages", []))
        message_count = len(messages)
        estimated_tokens = self.estimate_tokens(messages)
        if state.get("metadata", {}).get("compact_requested"):
            return CompactionDecision(True, "manual", message_count, estimated_tokens)
        if estimated_tokens > self.max_tokens_before_compact:
            return CompactionDecision(True, "token_threshold", message_count, estimated_tokens)
        if self.max_messages_before_compact is not None and message_count > self.max_messages_before_compact:
            return CompactionDecision(True, "message_threshold", message_count, estimated_tokens)
        return CompactionDecision(False, None, message_count, estimated_tokens)

    def should_compact(self, state: dict[str, Any]) -> bool:
        return self.compaction_decision(state).should_compact

    def compact_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Summarize older messages and return a state update preserving recent work and todos."""

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
