"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from typing import cast

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.graph.instrumentation import runtime_metrics_update
from langgraph_agent_blueprint.models import event
from langgraph_agent_blueprint.models.prompts import build_system_context


def _has_cached_memory(memory: dict[str, object] | None) -> bool:
    """Return True when state already contains a complete memory payload."""

    return isinstance(memory, dict) and {"user", "project", "session"}.issubset(memory.keys())


def context_builder_node(state: dict, deps: AppDependencies) -> dict:
    """Build the model-facing system context from project state, memory, tools, skills, and todos."""

    pre_update = run_hook_point(deps, state, "pre_context_build")
    if hook_blocked(pre_update):
        return pre_update
    current = state_with_update(state, pre_update)

    cached_memory = cast(
        dict[str, str] | None,
        current.get("memory") if _has_cached_memory(current.get("memory")) else None,
    )
    memory = cached_memory or deps.memory_service.load_memory(current.get("project_root"), current.get("session_id"))

    tools_summary = "Tools: " + ", ".join(sorted(current.get("available_tools", {})))
    skills_summary = "Skills: " + ", ".join(sorted(current.get("available_skills", {})))
    todos_summary = f"Todos: {current.get('todos', [])}" if current.get("todos") else ""
    plugin_fragments = current.get("plugin_state", {}).get("system_context_fragments", [])
    hook_fragments = current.get("metadata", {}).get("hook_system_context_fragments", [])
    context_provider_context = current.get("context_status", {}).get("context_provider_context", "")
    plugin_context = "\n\n".join(str(fragment) for fragment in [*plugin_fragments, *hook_fragments, context_provider_context] if fragment)
    memory_context = deps.memory_service.build_context(memory)
    system_context = build_system_context(
        current.get("project_root", ""),
        memory_context,
        tools_summary,
        skills_summary,
        todos_summary,
        plugin_context,
    )
    tokens = deps.compaction_service.estimate_tokens(current.get("messages", []))
    events = [event("node_finished", node="context_builder")]
    if any("Superpowers plugin is enabled." in str(fragment) for fragment in plugin_fragments):
        events.append(event("superpowers_bootstrap_applied", skill="superpowers/using-superpowers"))
    update = {
        "memory": memory,
        "context_status": {**current.get("context_status", {}), "estimated_tokens": tokens, "system_context": system_context},
        "ui_events": events,
        **runtime_metrics_update(
            current,
            {},
            extra_metrics={
                "memory_context_chars": len(memory_context),
                "memory_scope_count": len(memory),
                "context_builder_memory_cache_hit": cached_memory is not None,
            },
        ),
    }
    post_state = state_with_update(current, update)
    post_update = run_hook_point(deps, post_state, "post_context_build")
    return merge_updates(pre_update, update, post_update)

