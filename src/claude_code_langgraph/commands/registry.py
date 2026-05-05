"""CommandRegistry implementation for built-in, plugin, skill, and MCP command metadata."""

from __future__ import annotations

from typing import Any

from .base import Command
from .builtin import builtins


class CommandRegistry:
    """Registry for slash commands from built-ins, skills, plugins, and MCP."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command:
        if name not in self._commands:
            raise KeyError(f"Unknown command: {name}")
        return self._commands[name]

    def find(self, name: str) -> Command | None:
        return self._commands.get(name)

    def all(self) -> dict[str, Command]:
        return dict(self._commands)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        unsupported = {"rewind", "branch", "rename", "tag", "context", "plugins", "mcp"}
        return {
            name: {
                "name": command.name,
                "description": command.description,
                "type": command.type,
                "status": "unsupported" if name in unsupported else "enabled",
            }
            for name, command in self._commands.items()
        }


def build_builtin_command_registry() -> CommandRegistry:
    registry = CommandRegistry()
    for command in builtins():
        registry.register(command)
    return registry
