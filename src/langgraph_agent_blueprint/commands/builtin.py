"""Built-in slash command handlers that update graph state or request graph workflows."""

from __future__ import annotations

from typing import Any

from langgraph_agent_blueprint.config import format_config_explain, format_config_validate
from langgraph_agent_blueprint.models.config import EffectiveConfigReport

from .base import Command, CommandResult


def _help(args: str, state: dict[str, Any]) -> CommandResult:
    """Render enabled commands separately from optional unsupported command placeholders."""

    commands = state.get("available_commands", {})
    enabled = []
    unsupported = []
    for name, meta in sorted(commands.items()):
        if meta.get("status") == "unsupported":
            unsupported.append(f"/{name}")
        else:
            enabled.append(f"/{name}")
    response = f"Available commands: {', '.join(enabled) or '/help'}"
    if unsupported:
        response += f"\nUnsupported commands: {', '.join(unsupported)}"
    return CommandResult(True, response)


def _clear(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, "Conversation cleared.", metadata={"clear_messages": True})


def _compact(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(False, prompt=None, metadata={"compact_requested": True})


def _resume(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Resume requested for session: {args or 'latest'}", metadata={"resume": args or "latest"})


def _export(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, "Export requested.", metadata={"export_requested": True, "format": args or "markdown"})


def _skills(args: str, state: dict[str, Any]) -> CommandResult:
    """Render enabled skills with allowed tools and disabled skills with reasons."""

    skills = state.get("available_skills", {})
    builtin_skills = {name: meta for name, meta in skills.items() if not meta.get("plugin_name")}
    plugin_skills = {name: meta for name, meta in skills.items() if meta.get("plugin_name")}
    lines = ["Built-in skills:"]
    for name, meta in sorted(builtin_skills.items()):
        allowed = ", ".join(meta.get("allowed_tools", []) or [])
        lines.append(f"- {name}: {meta.get('description', '')} (allowed_tools: {allowed or 'none'})")
    if plugin_skills:
        lines.append("Plugin skills:")
        for name, meta in sorted(plugin_skills.items()):
            allowed = ", ".join(meta.get("allowed_tools", []) or [])
            lines.append(
                f"- {name}: {meta.get('description', '')} "
                f"(plugin: {meta.get('plugin_name')}, allowed_tools: {allowed or 'none'})"
            )
    disabled = state.get("disabled_skills", {})
    if disabled:
        lines.append("Disabled skills:")
        for name, reason in sorted(disabled.items()):
            lines.append(f"- {name}: {reason}")
    if len(lines) == 1:
        lines.append("- none")
    return CommandResult(True, "\n".join(lines))


def _plugins(args: str, state: dict[str, Any]) -> CommandResult:
    """Render installed/enabled plugin contributions."""

    plugin_state = state.get("plugin_state", {})
    plugins = plugin_state.get("plugins", [])
    if not plugins:
        return CommandResult(True, "Plugins: none")
    lines = ["Plugins:"]
    for plugin in sorted(plugins, key=lambda item: item.get("name", "")):
        bootstrap = plugin.get("bootstrap_skill") or "none"
        lines.append(
            f"- {plugin.get('name')}: {'enabled' if plugin.get('enabled', True) else 'disabled'}, version: {plugin.get('version', 'unknown')}, "
            f"skills: {plugin.get('skills_count', 0)}, hooks: {plugin.get('hooks_count', 0)}, "
            f"policies: {plugin.get('policies_count', 0)}, commands: {plugin.get('commands_count', 0)}, "
            f"tools: {plugin.get('tools_count', 0)}, mcp: {plugin.get('mcp_servers_count', 0)}, "
            f"context: {plugin.get('context_providers_count', 0)}, bootstrap: {bootstrap}"
        )
        if plugin.get("disabled_reason"):
            lines.append(f"  disabled: {plugin.get('disabled_reason')}")
        for warning in plugin.get("hook_warnings", []):
            lines.append(f"  hook warning: {warning.get('hook')}: {warning.get('error')}")
        for warning in plugin.get("policy_warnings", []):
            lines.append(f"  policy warning: {warning.get('policy')}: {warning.get('error')}")
        for warning in plugin.get("command_warnings", []):
            lines.append(f"  command warning: {warning.get('command')}: {warning.get('error')}")
        for warning in plugin.get("tool_warnings", []):
            lines.append(f"  tool warning: {warning.get('tool')}: {warning.get('error')}")
        for warning in plugin.get("mcp_warnings", []):
            lines.append(f"  mcp warning: {warning.get('server')}: {warning.get('error')}")
        for warning in plugin.get("context_warnings", []):
            lines.append(f"  context warning: {warning.get('context_provider')}: {warning.get('error')}")
    errors = plugin_state.get("errors", [])
    if errors:
        lines.append("Plugin errors:")
        for item in errors:
            lines.append(f"- {item.get('path')}: {item.get('error')}")
    warnings = plugin_state.get("hook_warnings", [])
    if warnings:
        lines.append("Plugin hook warnings:")
        for item in warnings:
            lines.append(f"- {item.get('plugin')}/{item.get('hook')}: {item.get('error')}")
    policy_warnings = plugin_state.get("policy_warnings", [])
    if policy_warnings:
        lines.append("Plugin policy warnings:")
        for item in policy_warnings:
            lines.append(f"- {item.get('plugin')}/{item.get('policy')}: {item.get('error')}")
    return CommandResult(True, "\n".join(lines))


def _hooks(args: str, state: dict[str, Any]) -> CommandResult:
    """Render registered hook contributions."""

    hooks = state.get("available_hooks") or state.get("hooks_state", {}).get("registered_hooks", [])
    if not hooks:
        return CommandResult(True, "Registered hooks: none")
    lines = ["Registered hooks:"]
    for hook in sorted(hooks, key=lambda item: (item.get("hook_point", ""), item.get("priority", 100), item.get("id", ""))):
        plugin = hook.get("plugin_name") or "core"
        status = "enabled" if hook.get("enabled", True) else "disabled"
        lines.append(f"- {hook.get('id')} [{hook.get('hook_point')}] plugin: {plugin}, priority: {hook.get('priority', 100)}, {status}")
    return CommandResult(True, "\n".join(lines))


def _status(args: str, state: dict[str, Any]) -> CommandResult:
    """Return compact runtime status for provider, paths, and registry sizes."""

    metadata = state.get("metadata", {})
    return CommandResult(
        True,
        "\n".join(
            [
                f"session_id: {state.get('session_id')}",
                f"provider/model: {metadata.get('config', {}).get('llm_provider', 'unknown')}/{metadata.get('model_name', 'unknown')}",
                f"project_root: {state.get('project_root')}",
                f"cwd: {state.get('cwd')}",
                f"storage_dir: {metadata.get('config', {}).get('storage_dir', 'unknown')}",
                f"tools: {len(state.get('available_tools', {}))}",
                f"skills: {len(state.get('available_skills', {}))}",
                f"commands: {len(state.get('available_commands', {}))}",
                f"langfuse: {'enabled' if state.get('observability_state', {}).get('enabled') else 'disabled'}",
            ]
        ),
    )


def _cost(args: str, state: dict[str, Any]) -> CommandResult:
    usage = state.get("usage", {})
    cost = usage.get("cost") if isinstance(usage, dict) else None
    return CommandResult(True, f"Usage: {usage}\nCost: {cost if cost is not None else 'unavailable'}")


def _config(args: str, state: dict[str, Any]) -> CommandResult:
    metadata = state.get("metadata", {})
    view = (args or "show").strip().split(maxsplit=1)[0] or "show"
    if view == "show":
        config = metadata.get("config", {})
        lines = [f"{key}: {value}" for key, value in sorted(config.items())]
        return CommandResult(True, "Config:\n" + "\n".join(lines))
    report_data = metadata.get("config_report")
    report = EffectiveConfigReport.model_validate(report_data) if isinstance(report_data, dict) else None
    if view == "explain":
        return CommandResult(True, format_config_explain(report))
    if view == "validate":
        return CommandResult(True, format_config_validate(report))
    return CommandResult(True, "Usage: /config [show|explain|validate]")


def _doctor(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, "Doctor requested.", metadata={"doctor_requested": True})


def _observability(args: str, state: dict[str, Any]) -> CommandResult:
    """Render observability backend status without exposing secrets."""

    status = state.get("observability_state", {})
    if not status:
        return CommandResult(True, "Langfuse: unavailable")
    enabled = "enabled" if status.get("enabled") else "disabled"
    lines = [
        f"Langfuse: {enabled}",
        f"mode: {status.get('mode')}",
        f"sdk_installed: {status.get('sdk_installed')}",
        f"base_url_configured: {status.get('base_url_configured')}",
        f"public_key_present: {status.get('public_key_present')}",
        f"secret_key_present: {status.get('secret_key_present')}",
        f"capture_inputs: {status.get('capture_inputs')}",
        f"capture_outputs: {status.get('capture_outputs')}",
    ]
    if status.get("last_error"):
        lines.append(f"last_error: {status.get('last_error')}")
    return CommandResult(True, "\n".join(lines))


def _mcp(args: str, state: dict[str, Any]) -> CommandResult:
    """Render MCP client status from graph-owned discovery state."""

    mcp_state = state.get("mcp_state", {})
    view = (args or "servers").strip().split()[0] if args or args == "" else "servers"
    servers = mcp_state.get("servers", [])
    tools = mcp_state.get("tools", {})
    resources = mcp_state.get("resources", {})
    prompts = mcp_state.get("prompts", {})
    invalid_servers = mcp_state.get("invalid_servers", [])
    if view in {"servers", "status"}:
        lines = ["MCP servers:"]
        if not servers:
            lines.append("- none")
        for server in servers:
            counts = {
                "tools": len([tool for tool in tools.values() if tool.get("server_name") == server.get("name")]),
                "resources": len(resources.get(server.get("name"), [])),
                "prompts": len(prompts.get(server.get("name"), [])),
            }
            detail = f", error: {server.get('error')}" if server.get("error") else ""
            lines.append(
                f"- {server.get('name')}: {server.get('status')} "
                f"(transport: {server.get('transport')}, tools: {counts['tools']}, "
                f"resources: {counts['resources']}, prompts: {counts['prompts']}){detail}"
            )
        if invalid_servers:
            lines.append("Invalid MCP servers:")
            for invalid in invalid_servers:
                lines.append(f"- {invalid.get('name')}: {invalid.get('error')}")
        return CommandResult(True, "\n".join(lines))
    if view == "tools":
        lines = ["MCP tools:"]
        if not tools:
            lines.append("- none")
        for name, tool in sorted(tools.items()):
            lines.append(f"- {name}: {tool.get('description', '')} (server: {tool.get('server_name')})")
        return CommandResult(True, "\n".join(lines))
    if view == "resources":
        lines = ["MCP resources:"]
        if not resources:
            lines.append("- none")
        for server, items in sorted(resources.items()):
            for item in items:
                lines.append(f"- {server}: {item.get('uri')} ({item.get('mime_type') or item.get('mimeType') or 'unknown'})")
        return CommandResult(True, "\n".join(lines))
    if view == "prompts":
        lines = ["MCP prompts:"]
        if not prompts:
            lines.append("- none")
        for server, items in sorted(prompts.items()):
            for item in items:
                lines.append(f"- {server}: {item.get('prompt_name')} ({item.get('description', '')})")
        return CommandResult(True, "\n".join(lines))
    return CommandResult(True, "Usage: /mcp [servers|tools|resources|prompts]")


def _context(args: str, state: dict[str, Any]) -> CommandResult:
    """Render resolved context references, fragments, and current budget status."""

    view = (args or "list").strip().split()[0] if args or args == "" else "list"
    if view == "clear":
        return CommandResult(True, "Context cleared.", metadata={"clear_context": True})
    references = state.get("context_references", [])
    fragments = state.get("resolved_context", [])
    budget = state.get("context_budget") or state.get("metadata", {}).get("context_budget", {})
    errors = state.get("context_status", {}).get("context_errors", [])
    lines = ["Context:"]
    if not references and not fragments and not errors:
        lines.append("- none")
    if references:
        lines.append("References:")
        for ref in references:
            label = ref.get("label") or ref.get("value")
            lines.append(f"- {ref.get('kind')}: {label}")
    if fragments:
        lines.append("Fragments:")
        for fragment in fragments:
            marker = " truncated" if fragment.get("truncated") else ""
            lines.append(
                f"- {fragment.get('title')} "
                f"({fragment.get('kind')}, trust: {fragment.get('trust')}, "
                f"tokens: {fragment.get('token_estimate', 0)}{marker})"
            )
    if isinstance(budget, dict) and budget:
        lines.append(
            f"Budget: {budget.get('used_tokens', 0)}/{budget.get('max_tokens', 0)} tokens, "
            f"included: {len(budget.get('included', []))}, "
            f"truncated: {len(budget.get('truncated', []))}, "
            f"dropped: {len(budget.get('dropped', []))}"
        )
    if errors:
        lines.append("Errors:")
        for item in errors:
            lines.append(f"- {item.get('type', 'context_error')}: {item.get('message', '')}")
    return CommandResult(True, "\n".join(lines))


def _memory(args: str, state: dict[str, Any]) -> CommandResult:
    """Render loaded memory scopes, omitting empty scopes for readability."""

    memory = state.get("memory", {})
    lines = []
    for scope in ["user", "project", "session"]:
        content = str(memory.get(scope, "")).strip()
        if content:
            lines.append(f"{scope}:\n{content}")
    return CommandResult(True, "\n\n".join(lines) if lines else "Memory scopes: none")


def _todo(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Todos: {state.get('todos', [])}")


def _prompt(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(False, prompt=args)


def _skill(args: str, state: dict[str, Any]) -> CommandResult:
    """Parse `/skill name args` into an active skill request for the graph skill route."""

    parts = args.split(maxsplit=1)
    name = parts[0] if parts else ""
    skill_args = parts[1] if len(parts) > 1 else ""
    return CommandResult(False, skill={"name": name, "args": skill_args})


def _not_implemented(name: str):
    def handler(args: str, state: dict[str, Any]) -> CommandResult:
        return CommandResult(True, f"/{name} is recognized but not implemented in the initial Python port.")

    return handler


def builtins() -> list[Command]:
    """Build the static list of built-in slash-command descriptors."""

    return [
        Command("help", "List commands", "local", _help),
        Command("clear", "Clear conversation", "local", _clear),
        Command("compact", "Compact context", "session", _compact),
        Command("resume", "Resume a session", "session", _resume),
        Command("export", "Export transcript", "local", _export),
        Command("skills", "List skills", "local", _skills),
        Command("status", "Show status", "local", _status),
        Command("cost", "Show usage/cost", "local", _cost),
        Command("config", "Show config", "local", _config),
        Command("doctor", "Run diagnostics", "diagnostic", _doctor),
        Command("observability", "Show observability status", "diagnostic", _observability),
        Command("memory", "Show memory", "local", _memory),
        Command("todo", "Show todos", "local", _todo),
        Command("prompt", "Expand a prompt command", "prompt", _prompt),
        Command("skill", "Invoke a skill", "skill", _skill),
        Command("rewind", "Rewind conversation", "session", _not_implemented("rewind")),
        Command("branch", "Project branch helper", "session", _not_implemented("branch")),
        Command("rename", "Rename session", "session", _not_implemented("rename")),
        Command("tag", "Tag session", "session", _not_implemented("tag")),
        Command("context", "Show context usage", "local", _context),
        Command("plugins", "List plugins", "local", _plugins),
        Command("hooks", "List hooks", "local", _hooks),
        Command("mcp", "List MCP state", "local", _mcp),
    ]
