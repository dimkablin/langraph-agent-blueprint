"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models import AgentActivityEvent, AgentActivitySource, event
from langgraph_agent_blueprint.tools import MCPToolAdapter
from langgraph_agent_blueprint.utils.activity import normalize_activity_namespace, safe_activity_data


def load_registries_node(state: dict, deps: AppDependencies) -> dict:
    plugin_state = deps.plugin_service.discover()
    mcp_state = deps.mcp_service.discover()
    _register_mcp_tools(deps, mcp_state)
    events = [event("node_finished", node="load_registries")]
    events.extend(mcp_state.get("events", []))
    for plugin in plugin_state.get("plugins", []):
        events.append(event("plugin_loaded", name=plugin.get("name"), skills_count=plugin.get("skills_count", 0)))
    for skill_name in plugin_state.get("skills", []):
        events.append(
            event(
                "plugin_skill_registered",
                name=skill_name,
                activity=_skill_discovered_activity(skill_name).model_dump(mode="json"),
            )
        )
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
            "invalid_servers": mcp_state.get("invalid_servers", []),
            "warnings": mcp_state.get("warnings", []),
            "errors": mcp_state.get("errors", []),
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


def _register_mcp_tools(deps: AppDependencies, mcp_state: dict) -> None:
    """Register discovered MCP tools after explicit graph discovery."""

    for definition in mcp_state.get("tools", {}).values():
        adapter = MCPToolAdapter(definition, deps.mcp_service)
        try:
            deps.tool_registry.get(adapter.name)
        except KeyError:
            deps.tool_registry.register(adapter)


def _skill_discovered_activity(skill_name: str) -> AgentActivityEvent:
    return AgentActivityEvent(
        type=f"skill.{normalize_activity_namespace(skill_name)}.discovered",
        source=AgentActivitySource(kind="skill", name=skill_name, component="SkillRegistry"),
        category="skill",
        status="success",
        title="Skill discovered",
        summary=f"Discovered skill {skill_name}.",
        data=safe_activity_data({"name": skill_name, "source_type": "plugin"}),
    )
