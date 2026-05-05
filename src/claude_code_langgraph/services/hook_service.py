"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from claude_code_langgraph.models.messages import event


Hook = Callable[[dict[str, Any]], dict[str, Any] | None]


class HookService:
    """Lifecycle hook dispatcher that isolates hook failures by default."""

    def __init__(self, crash_on_error: bool = False) -> None:
        self.crash_on_error = crash_on_error
        self._hooks: dict[str, list[Hook]] = {}

    def register(self, name: str, hook: Hook) -> None:
        self._hooks.setdefault(name, []).append(hook)

    def run(self, name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Run hooks for a lifecycle point and convert failures into structured events."""

        results: list[dict[str, Any]] = []
        for hook in self._hooks.get(name, []):
            try:
                output = hook(payload) or {}
                results.append(event("hook_finished", hook=name, output=output))
            except Exception as exc:
                if self.crash_on_error:
                    raise
                results.append(event("hook_error", hook=name, error=str(exc)))
        return results

