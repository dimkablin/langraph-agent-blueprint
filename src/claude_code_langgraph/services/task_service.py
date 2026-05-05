from __future__ import annotations

from typing import Any

from claude_code_langgraph.utils.ids import new_id


class TaskService:
    """In-state task/todo helpers."""

    def create_task(self, prompt: str) -> dict[str, Any]:
        return {"id": new_id("task"), "prompt": prompt, "status": "pending"}

    def update_todos(self, todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return todos

