from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.prompts import build_system_context
from claude_code_langgraph.models.messages import event


def context_builder_node(state: dict, deps: AppDependencies) -> dict:
    memory = deps.memory_service.load_memory(state.get("project_root"), state.get("session_id"))
    tools_summary = "Tools: " + ", ".join(sorted(state.get("available_tools", {})))
    skills_summary = "Skills: " + ", ".join(sorted(state.get("available_skills", {})))
    todos_summary = f"Todos: {state.get('todos', [])}" if state.get("todos") else ""
    system_context = build_system_context(
        state.get("project_root", ""),
        deps.memory_service.build_context(memory),
        tools_summary,
        skills_summary,
        todos_summary,
    )
    tokens = deps.compaction_service.estimate_tokens(state.get("messages", []))
    return {
        "memory": memory,
        "context_status": {**state.get("context_status", {}), "estimated_tokens": tokens, "system_context": system_context},
        "ui_events": [event("node_finished", node="context_builder")],
    }

