"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from langgraph_agent_blueprint.commands import CommandRegistry


class CommandService:
    """Thin service wrapper around the command registry."""

    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry

