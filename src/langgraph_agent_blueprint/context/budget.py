"""Context fragment budget and truncation helpers."""

from __future__ import annotations

from langgraph_agent_blueprint.models.context import ContextBudgetReport, ContextFragment


class ContextBudgetService:
    """Apply a cheap token budget to resolved context fragments."""

    def __init__(self, max_tokens: int = 8000) -> None:
        self.max_tokens = max(1, int(max_tokens))

    def estimate_tokens(self, text: str) -> int:
        return max(1, (len(text) + 3) // 4)

    def apply(self, fragments: list[ContextFragment]) -> tuple[list[ContextFragment], ContextBudgetReport]:
        included: list[ContextFragment] = []
        dropped: list[dict[str, object]] = []
        truncated: list[dict[str, object]] = []
        used = 0
        for fragment in fragments:
            estimate = fragment.token_estimate or self.estimate_tokens(fragment.content)
            remaining = self.max_tokens - used
            if remaining <= 0:
                dropped.append({"id": fragment.id, "title": fragment.title, "reason": "context budget exhausted"})
                continue
            if estimate <= remaining:
                included.append(fragment.model_copy(update={"token_estimate": estimate}))
                used += estimate
                continue
            max_chars = max(1, remaining * 4)
            content = fragment.content[:max_chars].rstrip() + "\n[truncated]"
            actual = self.estimate_tokens(content)
            included.append(fragment.model_copy(update={"content": content, "token_estimate": min(actual, remaining), "truncated": True}))
            used += min(actual, remaining)
            truncated.append({"id": fragment.id, "title": fragment.title, "reason": "context budget"})
        report = ContextBudgetReport(
            max_tokens=self.max_tokens,
            used_tokens=used,
            dropped=dropped,
            truncated=truncated,
            included=[fragment.id for fragment in included],
        )
        return included, report
