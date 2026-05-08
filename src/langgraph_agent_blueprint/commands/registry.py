"""CommandRegistry implementation for built-in, plugin, skill, and MCP command metadata."""

from __future__ import annotations

from typing import Any

from langgraph_agent_blueprint.models import CommandResult, PluginCommandContribution, PluginContribution

from .base import Command
from .builtin import builtins


class CommandRegistry:
    """Registry for slash commands from built-ins, skills, plugins, and MCP."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def register_plugin_contributions(self, contributions: list[PluginContribution]) -> None:
        """Register declarative plugin commands with deterministic conflict handling."""

        for contribution in contributions:
            if not contribution.enabled:
                continue
            for command in contribution.commands:
                if not command.enabled:
                    continue
                self.register(_plugin_command_descriptor(command, self._commands))

    def get(self, name: str) -> Command:
        if name not in self._commands:
            raise KeyError(f"Unknown command: {name}")
        return self._commands[name]

    def find(self, name: str) -> Command | None:
        return self._commands.get(name)

    def all(self) -> dict[str, Command]:
        return dict(self._commands)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        unsupported = {"rewind", "branch", "rename", "tag"}
        return {
            name: {
                "name": command.name,
                "description": command.description,
                "type": command.type,
                "status": "unsupported" if name in unsupported else "enabled",
                "plugin_name": command.plugin_name,
            }
            for name, command in self._commands.items()
        }


def build_builtin_command_registry() -> CommandRegistry:
    registry = CommandRegistry()
    for command in builtins():
        registry.register(command)
    return registry


def _plugin_command_descriptor(contribution: PluginCommandContribution, existing: dict[str, Command]) -> Command:
    registry_name = contribution.registry_name or contribution.name
    if registry_name in existing:
        registry_name = f"{contribution.plugin_name}.{contribution.name}"
    description = contribution.description or f"{contribution.plugin_name} plugin command"

    if contribution.command_type == "static_response":
        response = contribution.response or ""

        def handler(args: str, state: dict[str, Any]) -> CommandResult:
            return CommandResult(True, response)

        return Command(registry_name, description, "local", handler, plugin_name=contribution.plugin_name)

    if contribution.command_type == "prompt":
        template = contribution.prompt or "{args}"

        def handler(args: str, state: dict[str, Any]) -> CommandResult:
            return CommandResult(False, prompt=template.replace("{args}", args))

        return Command(registry_name, description, "prompt", handler, plugin_name=contribution.plugin_name)

    skill_name = contribution.skill or ""
    if skill_name and "/" not in skill_name:
        skill_name = f"{contribution.plugin_name}/{skill_name}"

    def handler(args: str, state: dict[str, Any]) -> CommandResult:
        return CommandResult(False, skill={"name": skill_name, "args": args})

    return Command(registry_name, description, "skill", handler, plugin_name=contribution.plugin_name)
