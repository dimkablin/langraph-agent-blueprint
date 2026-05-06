"""Built-in slash command handlers that update graph state or request graph workflows."""

from __future__ import annotations

from typing import Any

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
            f"- {plugin.get('name')}: enabled, version: {plugin.get('version', 'unknown')}, "
            f"skills: {plugin.get('skills_count', 0)}, bootstrap: {bootstrap}"
        )
    errors = plugin_state.get("errors", [])
    if errors:
        lines.append("Plugin errors:")
        for item in errors:
            lines.append(f"- {item.get('path')}: {item.get('error')}")
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
            ]
        ),
    )


def _cost(args: str, state: dict[str, Any]) -> CommandResult:
    usage = state.get("usage", {})
    cost = usage.get("cost") if isinstance(usage, dict) else None
    return CommandResult(True, f"Usage: {usage}\nCost: {cost if cost is not None else 'unavailable'}")


def _config(args: str, state: dict[str, Any]) -> CommandResult:
    config = state.get("metadata", {}).get("config", {})
    lines = [f"{key}: {value}" for key, value in sorted(config.items())]
    return CommandResult(True, "Config:\n" + "\n".join(lines))


def _doctor(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, "Doctor requested.", metadata={"doctor_requested": True})


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
        Command("memory", "Show memory", "local", _memory),
        Command("todo", "Show todos", "local", _todo),
        Command("prompt", "Expand a prompt command", "prompt", _prompt),
        Command("skill", "Invoke a skill", "skill", _skill),
        Command("rewind", "Rewind conversation", "session", _not_implemented("rewind")),
        Command("branch", "Project branch helper", "session", _not_implemented("branch")),
        Command("rename", "Rename session", "session", _not_implemented("rename")),
        Command("tag", "Tag session", "session", _not_implemented("tag")),
        Command("context", "Show context usage", "local", _not_implemented("context")),
        Command("plugins", "List plugins", "local", _plugins),
        Command("mcp", "List MCP state", "local", _not_implemented("mcp")),
    ]
