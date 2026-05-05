"""Utility module containing small reusable helpers used across the runtime."""

from __future__ import annotations


def truncate_text(text: str, limit: int) -> tuple[str, bool]:
    """Truncate text to a configured character limit."""

    if len(text) <= limit:
        return text, False
    suffix = f"\n...[truncated {len(text) - limit} chars]"
    return text[: max(0, limit - len(suffix))] + suffix, True

