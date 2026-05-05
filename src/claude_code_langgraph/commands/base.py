from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal


CommandType = Literal["local", "prompt", "skill", "session", "diagnostic"]


@dataclass(frozen=True)
class CommandResult:
    handled: bool
    response: str | None = None
    prompt: str | None = None
    skill: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


CommandHandler = Callable[[str, dict[str, Any]], CommandResult]


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    type: CommandType
    handler: CommandHandler

    def execute(self, args: str, state: dict[str, Any]) -> CommandResult:
        return self.handler(args, state)

