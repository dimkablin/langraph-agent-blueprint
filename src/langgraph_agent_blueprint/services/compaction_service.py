"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage

from langgraph_agent_blueprint.models.llm import provider_tool_schemas


CompactionReason = Literal["manual", "token_threshold", "message_threshold", "context_window"]


@dataclass(frozen=True)
class CompactionDecision:
    """Typed result of evaluating whether a state should be compacted."""

    should_compact: bool
    reason: CompactionReason | None
    message_count: int
    estimated_tokens: int
    context_window_tokens: int | None = None
    prompt_tokens: int | None = None
    overflow_tokens: int = 0


class CompactionService:
    """Context accounting and compaction preserving active work."""

    def __init__(
        self,
        max_tokens_before_compact: int = 12_000,
        keep_recent: int = 6,
        max_messages_before_compact: int | None = None,
        context_window_max_tokens: int | None = None,
        context_window_reserve_tokens: int = 0,
        max_summary_tokens: int = 500,
    ) -> None:
        self.max_tokens_before_compact = max_tokens_before_compact
        self.keep_recent = keep_recent
        self.max_messages_before_compact = max_messages_before_compact
        self.context_window_max_tokens = context_window_max_tokens
        self.context_window_reserve_tokens = max(0, context_window_reserve_tokens)
        self.max_summary_tokens = max(64, max_summary_tokens)

    def estimate_tokens(self, messages: list[BaseMessage]) -> int:
        return sum(max(1, len(str(getattr(message, "content", ""))) // 4) for message in messages)

    def compaction_decision(self, state: dict[str, Any]) -> CompactionDecision:
        """Return a typed compaction decision for the current runtime state."""

        messages = list(state.get("messages", []))
        message_count = len(messages)
        estimated_tokens = self.estimate_tokens(messages)
        pressure = self.context_window_pressure(state, messages=messages)
        if state.get("metadata", {}).get("compact_requested"):
            return CompactionDecision(
                True,
                "manual",
                message_count,
                estimated_tokens,
                context_window_tokens=pressure.get("context_window_tokens") if pressure else None,
                prompt_tokens=pressure.get("prompt_tokens") if pressure else None,
                overflow_tokens=int(pressure.get("overflow_tokens", 0)) if pressure else 0,
            )
        if pressure and pressure["overflow_tokens"] > 0 and messages:
            return CompactionDecision(
                True,
                "context_window",
                message_count,
                estimated_tokens,
                context_window_tokens=pressure["context_window_tokens"],
                prompt_tokens=pressure["prompt_tokens"],
                overflow_tokens=pressure["overflow_tokens"],
            )
        if estimated_tokens > self.max_tokens_before_compact:
            return CompactionDecision(
                True,
                "token_threshold",
                message_count,
                estimated_tokens,
                context_window_tokens=pressure.get("context_window_tokens") if pressure else None,
                prompt_tokens=pressure.get("prompt_tokens") if pressure else None,
                overflow_tokens=int(pressure.get("overflow_tokens", 0)) if pressure else 0,
            )
        if self.max_messages_before_compact is not None and message_count > self.max_messages_before_compact:
            return CompactionDecision(
                True,
                "message_threshold",
                message_count,
                estimated_tokens,
                context_window_tokens=pressure.get("context_window_tokens") if pressure else None,
                prompt_tokens=pressure.get("prompt_tokens") if pressure else None,
                overflow_tokens=int(pressure.get("overflow_tokens", 0)) if pressure else 0,
            )
        return CompactionDecision(
            False,
            None,
            message_count,
            estimated_tokens,
            context_window_tokens=pressure.get("context_window_tokens") if pressure else None,
            prompt_tokens=pressure.get("prompt_tokens") if pressure else None,
            overflow_tokens=int(pressure.get("overflow_tokens", 0)) if pressure else 0,
        )

    def should_compact(self, state: dict[str, Any]) -> bool:
        return self.compaction_decision(state).should_compact

    def context_window_pressure(self, state: dict[str, Any], *, messages: list[BaseMessage] | None = None) -> dict[str, int] | None:
        """Estimate whether the next model prompt can fit in the configured context window."""

        context_window = int(self.context_window_max_tokens or 0)
        if context_window <= 0:
            return None
        messages = list(messages if messages is not None else state.get("messages", []))
        overhead_tokens = self._state_prompt_overhead_tokens(state)
        message_tokens = self.estimate_tokens(messages)
        prompt_tokens = overhead_tokens + message_tokens
        usable_window = max(context_window - self.context_window_reserve_tokens, 0)
        message_budget = max(usable_window - overhead_tokens, 0)
        return {
            "context_window_tokens": context_window,
            "usable_window_tokens": usable_window,
            "overhead_tokens": overhead_tokens,
            "message_tokens": message_tokens,
            "message_budget_tokens": message_budget,
            "prompt_tokens": prompt_tokens,
            "overflow_tokens": max(prompt_tokens - usable_window, 0),
        }

    def compact_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Summarize older messages and return a state update preserving recent work and todos."""

        messages = list(state.get("messages", []))
        old, recent = self._split_messages_for_compaction(messages)
        old, recent = self._fit_recent_tail_for_context_budget(state, old, recent)
        summary_token_budget = self._summary_token_budget(state, recent)
        summary = self._build_summary(old, summary_token_budget)
        compacted_messages = [SystemMessage(content=f"Compacted prior context:\n{summary}"), *recent]
        compacted_messages = self._fit_compacted_messages_to_context_budget(state, compacted_messages)
        return {
            "messages": compacted_messages,
            "todos": list(state.get("todos", [])),
            "context_status": {
                **state.get("context_status", {}),
                "compacted": True,
                "summary": summary,
                "estimated_tokens": self.estimate_tokens(compacted_messages),
                "tokens_before_compact": self.estimate_tokens(messages),
                "recent_messages_after_compact": len(recent),
            },
        }

    def _split_messages_for_compaction(self, messages: list[BaseMessage]) -> tuple[list[BaseMessage], list[BaseMessage]]:
        if not messages:
            return [], []
        keep_count = min(self.keep_recent, max(1, len(messages) // 2))
        keep_start = max(0, len(messages) - keep_count)
        keep_start = self._tool_pair_safe_keep_start(messages, keep_start)
        return messages[:keep_start], messages[keep_start:]

    def _tool_pair_safe_keep_start(self, messages: list[BaseMessage], keep_start: int) -> int:
        """Avoid splitting an assistant tool-call message from its matching tool result."""

        if keep_start <= 0 or keep_start >= len(messages):
            return keep_start
        first_recent = messages[keep_start]
        if not isinstance(first_recent, ToolMessage):
            return keep_start

        tool_result_ids: set[str] = set()
        for message in messages[keep_start:]:
            if not isinstance(message, ToolMessage):
                break
            tool_id = getattr(message, "tool_call_id", "")
            if tool_id:
                tool_result_ids.add(str(tool_id))
        if not tool_result_ids:
            return keep_start

        for index in range(keep_start - 1, -1, -1):
            message = messages[index]
            if not isinstance(message, AIMessage):
                continue
            call_ids = {
                str(call.get("id"))
                for call in list(getattr(message, "tool_calls", []) or [])
                if isinstance(call, dict) and call.get("id")
            }
            if call_ids & tool_result_ids:
                return index
        return keep_start

    def _summary_token_budget(self, state: dict[str, Any], recent: list[BaseMessage]) -> int:
        pressure = self.context_window_pressure(state)
        if not pressure:
            return self.max_summary_tokens
        remaining = pressure["message_budget_tokens"] - self.estimate_tokens(recent)
        if remaining <= 0:
            return 1
        return max(1, min(self.max_summary_tokens, remaining))

    def _build_summary(self, messages: list[BaseMessage], token_budget: int) -> str:
        if not messages:
            return "No earlier messages were available before the recent context tail."
        max_chars = max(1, token_budget * 4)
        lines = []
        for index, message in enumerate(messages, start=1):
            role = str(getattr(message, "type", message.__class__.__name__))
            content = self._message_summary_content(message)
            if content:
                lines.append(f"{index}. {role}: {content}")
        summary = "\n".join(lines) or "Earlier messages contained no text content."
        if len(summary) <= max_chars:
            return summary
        marker = "\n[compaction summary truncated to fit context window]"
        if max_chars <= len(marker):
            return marker[:max_chars]
        return summary[: max(1, max_chars - len(marker))].rstrip() + marker

    def _message_summary_content(self, message: BaseMessage) -> str:
        content = str(getattr(message, "content", "") or "").replace("\r\n", "\n").strip()
        if isinstance(message, AIMessage):
            tool_calls = [
                f"{call.get('name')}#{call.get('id')}"
                for call in list(getattr(message, "tool_calls", []) or [])
                if isinstance(call, dict)
            ]
            if tool_calls:
                tool_text = "tool calls: " + ", ".join(tool_calls)
                content = f"{content} ({tool_text})" if content else tool_text
        if isinstance(message, ToolMessage):
            tool_id = getattr(message, "tool_call_id", "")
            content = f"tool result {tool_id}: {content}" if tool_id else f"tool result: {content}"
        return content

    def _has_compactable_history(self, messages: list[BaseMessage]) -> bool:
        old, _recent = self._split_messages_for_compaction(messages)
        return bool(old)

    def _fit_recent_tail_for_context_budget(
        self,
        state: dict[str, Any],
        old: list[BaseMessage],
        recent: list[BaseMessage],
    ) -> tuple[list[BaseMessage], list[BaseMessage]]:
        message_budget = self._message_budget_tokens(state)
        if message_budget is None or message_budget <= 0 or not recent:
            return old, recent
        summary_reserve = min(64, max(1, message_budget // 4)) if old else 0
        recent_budget = max(1, message_budget - summary_reserve)
        fitted, moved = self._select_recent_tail(recent, recent_budget)
        return [*old, *moved], fitted

    def _select_recent_tail(self, messages: list[BaseMessage], token_budget: int) -> tuple[list[BaseMessage], list[BaseMessage]]:
        selected_blocks: list[list[BaseMessage]] = []
        remaining = max(1, token_budget)
        start = len(messages)
        while start > 0:
            candidate_start = self._tool_pair_safe_keep_start(messages, start - 1)
            block = messages[candidate_start:start]
            block_tokens = self.estimate_tokens(block)
            if block_tokens <= remaining:
                selected_blocks.append(block)
                remaining -= block_tokens
                start = candidate_start
                continue
            if not selected_blocks:
                selected_blocks.append(self._truncate_message_block_to_budget(block, remaining))
                start = candidate_start
            break
        selected: list[BaseMessage] = []
        for block in reversed(selected_blocks):
            selected.extend(block)
        return selected, messages[:start]

    def _truncate_message_block_to_budget(self, block: list[BaseMessage], token_budget: int) -> list[BaseMessage]:
        remaining = max(1, token_budget)
        selected: list[BaseMessage] = []
        for message in reversed(block):
            tokens = self.estimate_tokens([message])
            if tokens <= remaining:
                selected.append(message)
                remaining -= tokens
                continue
            if not selected:
                selected.append(self._message_with_truncated_content(message, remaining))
            break
        return list(reversed(selected))

    def _fit_compacted_messages_to_context_budget(
        self,
        state: dict[str, Any],
        messages: list[BaseMessage],
    ) -> list[BaseMessage]:
        message_budget = self._message_budget_tokens(state)
        if message_budget is None or self.estimate_tokens(messages) <= message_budget:
            return messages
        fitted, _moved = self._select_recent_tail(messages, message_budget)
        if fitted and isinstance(fitted[0], SystemMessage):
            return fitted
        summary = messages[0] if messages and isinstance(messages[0], SystemMessage) else None
        tail_budget = max(1, message_budget - self.estimate_tokens([summary]) if summary is not None else message_budget)
        tail, _moved_tail = self._select_recent_tail(messages[1:] if summary is not None else messages, tail_budget)
        if summary is None:
            return tail
        remaining_for_summary = max(1, message_budget - self.estimate_tokens(tail))
        return [self._message_with_truncated_content(summary, remaining_for_summary), *tail]

    def _message_budget_tokens(self, state: dict[str, Any]) -> int | None:
        pressure = self.context_window_pressure(state, messages=[])
        if not pressure:
            return None
        return max(1, int(pressure["message_budget_tokens"]))

    def _message_with_truncated_content(self, message: BaseMessage, token_budget: int) -> BaseMessage:
        content = self._message_summary_content(message)
        max_chars = max(1, token_budget * 4)
        if len(content) > max_chars:
            marker = "\n[truncated to fit context window]"
            if max_chars <= len(marker):
                content = marker[:max_chars]
            else:
                content = content[: max(1, max_chars - len(marker))].rstrip() + marker
        if hasattr(message, "model_copy"):
            return message.model_copy(update={"content": content})
        return message

    def _state_prompt_overhead_tokens(self, state: dict[str, Any]) -> int:
        context_status = state.get("context_status", {}) if isinstance(state.get("context_status"), dict) else {}
        system_context = str(context_status.get("system_context") or "")
        overhead_chars = len(system_context)
        overhead_chars += self._json_size(provider_tool_schemas(state.get("available_tools", {})))
        return max(0, (overhead_chars + 3) // 4)

    @staticmethod
    def _json_size(payload: object) -> int:
        try:
            return len(json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True))
        except TypeError:
            return len(str(payload))
