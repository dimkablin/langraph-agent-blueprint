"""Core command dataclasses and type aliases used by the slash-command registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from langgraph_agent_blueprint.models.commands import CommandResult


CommandType = Literal["local", "prompt", "skill", "session", "diagnostic"]


CommandHandler = Callable[[str, dict[str, Any]], CommandResult]


@dataclass(frozen=True)
class Command:
    """Immutable slash-command descriptor registered in the CommandRegistry."""
    name: str
    description: str
    type: CommandType
    handler: CommandHandler
    plugin_name: str | None = None

    def execute(self, args: str, state: dict[str, Any]) -> CommandResult:
        return self.handler(args, state)

