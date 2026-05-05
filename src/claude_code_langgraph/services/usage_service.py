"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from typing import Any


class UsageService:
    """Aggregates token/tool usage into graph state."""

    @staticmethod
    def merge(existing: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        merged = dict(existing or {})
        for key in ["input_tokens", "output_tokens", "total_tokens", "tool_calls"]:
            merged[key] = int(merged.get(key, 0)) + int(update.get(key, 0))
        for key in ["model", "provider", "duration_ms", "cost"]:
            if update.get(key) is not None:
                merged[key] = update[key]
        return merged

