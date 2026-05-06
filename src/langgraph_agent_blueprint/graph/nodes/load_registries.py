"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models.messages import event


def load_registries_node(state: dict, deps: AppDependencies) -> dict:
    plugin_state = deps.plugin_service.discover()
    mcp_state = deps.mcp_service.discover()
    events = [event("node_finished", node="load_registries")]
    for plugin in plugin_state.get("plugins", []):
        events.append(event("plugin_loaded", name=plugin.get("name"), skills_count=plugin.get("skills_count", 0)))
    for skill_name in plugin_state.get("skills", []):
        events.append(event("plugin_skill_registered", name=skill_name))
    return {
        "available_tools": deps.tool_registry.snapshot(),
        "available_commands": deps.command_registry.snapshot(),
        "available_skills": deps.skill_registry.snapshot(),
        "disabled_skills": dict(deps.skill_registry.disabled),
        "plugin_state": plugin_state,
        "mcp_state": {"tools": list(mcp_state["tools"]), "resources": mcp_state["resources"], "prompts": mcp_state["prompts"]},
        "ui_events": events,
    }
