from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def load_registries_node(state: dict, deps: AppDependencies) -> dict:
    plugin_state = deps.plugin_service.discover()
    mcp_state = deps.mcp_service.discover()
    return {
        "available_tools": deps.tool_registry.snapshot(),
        "available_commands": deps.command_registry.snapshot(),
        "available_skills": deps.skill_registry.snapshot(),
        "disabled_skills": dict(deps.skill_registry.disabled),
        "plugin_state": plugin_state,
        "mcp_state": {"tools": list(mcp_state["tools"]), "resources": mcp_state["resources"], "prompts": mcp_state["prompts"]},
        "ui_events": [event("node_finished", node="load_registries")],
    }
