from __future__ import annotations

from typing import Any

from .base import Command, CommandResult


def _help(args: str, state: dict[str, Any]) -> CommandResult:
    commands = state.get("available_commands", {})
    names = ", ".join(f"/{name}" for name in sorted(commands)) or "/help"
    return CommandResult(True, f"Available commands: {names}")


def _clear(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, "Conversation cleared.", metadata={"clear_messages": True})


def _compact(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(False, prompt=None, metadata={"compact_requested": True})


def _resume(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Resume requested for session: {args or 'latest'}", metadata={"resume": args or "latest"})


def _export(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, "Export requested.", metadata={"export_requested": True, "format": args or "markdown"})


def _skills(args: str, state: dict[str, Any]) -> CommandResult:
    skills = state.get("available_skills", {})
    names = ", ".join(sorted(skills)) or "none"
    return CommandResult(True, f"Available skills: {names}")


def _status(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Session {state.get('session_id')} using model {state.get('metadata', {}).get('model_name', 'unknown')}")


def _cost(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Usage: {state.get('usage', {})}")


def _config(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Config: {state.get('metadata', {}).get('config', {})}")


def _doctor(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, "Doctor command is available. Use the diagnostics tool for detailed checks.")


def _memory(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Memory scopes: {', '.join(state.get('memory', {}).keys()) or 'none'}")


def _todo(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(True, f"Todos: {state.get('todos', [])}")


def _prompt(args: str, state: dict[str, Any]) -> CommandResult:
    return CommandResult(False, prompt=args)


def _skill(args: str, state: dict[str, Any]) -> CommandResult:
    parts = args.split(maxsplit=1)
    name = parts[0] if parts else ""
    skill_args = parts[1] if len(parts) > 1 else ""
    return CommandResult(False, skill={"name": name, "args": skill_args})


def _not_implemented(name: str):
    def handler(args: str, state: dict[str, Any]) -> CommandResult:
        return CommandResult(True, f"/{name} is recognized but not implemented in the initial Python port.")

    return handler


def builtins() -> list[Command]:
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
        Command("plugins", "List plugins", "local", _not_implemented("plugins")),
        Command("mcp", "List MCP state", "local", _not_implemented("mcp")),
    ]

