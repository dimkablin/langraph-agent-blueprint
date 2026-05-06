"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models.prompts import build_system_context
from langgraph_agent_blueprint.models.messages import event


def context_builder_node(state: dict, deps: AppDependencies) -> dict:
    """Build the model-facing system context from project state, memory, tools, skills, and todos."""

    memory = deps.memory_service.load_memory(state.get("project_root"), state.get("session_id"))
    tools_summary = "Tools: " + ", ".join(sorted(state.get("available_tools", {})))
    skills_summary = "Skills: " + ", ".join(sorted(state.get("available_skills", {})))
    todos_summary = f"Todos: {state.get('todos', [])}" if state.get("todos") else ""
    plugin_fragments = state.get("plugin_state", {}).get("system_context_fragments", [])
    plugin_context = "\n\n".join(str(fragment) for fragment in plugin_fragments if fragment)
    system_context = build_system_context(
        state.get("project_root", ""),
        deps.memory_service.build_context(memory),
        tools_summary,
        skills_summary,
        todos_summary,
        plugin_context,
    )
    tokens = deps.compaction_service.estimate_tokens(state.get("messages", []))
    events = [event("node_finished", node="context_builder")]
    if any("Superpowers plugin is enabled." in str(fragment) for fragment in plugin_fragments):
        events.append(event("superpowers_bootstrap_applied", skill="superpowers/using-superpowers"))
    return {
        "memory": memory,
        "context_status": {**state.get("context_status", {}), "estimated_tokens": tokens, "system_context": system_context},
        "ui_events": events,
    }

