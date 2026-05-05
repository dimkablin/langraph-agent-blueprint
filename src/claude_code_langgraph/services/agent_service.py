"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from typing import Any

from claude_code_langgraph.utils.ids import new_id


class AgentService:
    """Child-run service used by agent subgraphs and AgentTool."""

    def run_child(self, prompt: str, parent_state: dict[str, Any]) -> dict[str, Any]:
        child_id = new_id("child")
        return {
            "id": child_id,
            "status": "completed",
            "prompt": prompt,
            "result": f"Subagent completed: {prompt}",
            "parent_session_id": parent_state.get("session_id"),
        }

