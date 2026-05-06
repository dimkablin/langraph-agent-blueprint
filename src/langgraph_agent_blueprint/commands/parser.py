"""Slash-command parser that separates command names from their argument text."""

from __future__ import annotations

from langgraph_agent_blueprint.models.commands import CommandType, ParsedCommand


def parse_slash_command(text: str) -> ParsedCommand | None:
    """Parse `/name args` into command name and argument string."""

    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped[1:].split(maxsplit=1)
    name = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(name=name, args=args, raw=stripped, command_type=_command_type(name))


def _command_type(name: str) -> CommandType:
    """Classify built-in command names without consulting runtime registries."""

    if name == "skill":
        return "skill"
    if name == "prompt":
        return "prompt"
    if name in {"compact", "resume", "rewind", "branch", "rename", "tag"}:
        return "session"
    if name == "doctor":
        return "diagnostic"
    if name in {"help", "clear", "export", "skills", "status", "cost", "config", "memory", "todo", "context", "plugins", "hooks", "mcp"}:
        return "local"
    return "unsupported"

