"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models.messages import event


def load_registries_node(state: dict, deps: AppDependencies) -> dict:
    plugin_state = deps.plugin_service.discover()
    mcp_state = deps.mcp_service.discover()
    events = [event("node_finished", node="load_registries")]
    events.extend(mcp_state.get("events", []))
    for plugin in plugin_state.get("plugins", []):
        events.append(event("plugin_loaded", name=plugin.get("name"), skills_count=plugin.get("skills_count", 0)))
    for skill_name in plugin_state.get("skills", []):
        events.append(event("plugin_skill_registered", name=skill_name))
    metadata = dict(state.get("metadata", {}))
    run_session_start = not metadata.get("session_start_hooks_ran")
    if run_session_start:
        metadata["session_start_hooks_ran"] = True
    update = {
        "available_tools": deps.tool_registry.snapshot(),
        "available_commands": deps.command_registry.snapshot(),
        "available_skills": deps.skill_registry.snapshot(),
        "available_hooks": deps.hook_registry.snapshot(),
        "disabled_skills": dict(deps.skill_registry.disabled),
        "plugin_state": plugin_state,
        "mcp_state": {
            "servers": mcp_state.get("servers", []),
            "tools": mcp_state.get("tools", {}),
            "resources": mcp_state.get("resources", {}),
            "prompts": mcp_state.get("prompts", {}),
            "transport_support": mcp_state.get("transport_support", {}),
        },
        "hooks_state": {"registered_hooks": deps.hook_registry.snapshot(), "registered_hook_count": len(deps.hook_registry.list_hooks())},
        "observability_state": deps.observability_service.status(),
        "metadata": metadata,
        "ui_events": events,
    }
    if not run_session_start:
        return update
    hook_update = run_hook_point(deps, state_with_update(state, update), "session_start")
    return merge_updates(update, hook_update)
