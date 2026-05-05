from __future__ import annotations

from typing import Any

from .registry import SkillRegistry


class SkillInvocationService:
    """Resolves, renders, and records skill invocations."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def invoke(self, name: str, args: str, state: dict[str, Any]) -> dict[str, Any]:
        skill = self.registry.get(name)
        prompt = skill.render(args, state)
        return {
            "name": name,
            "args": args,
            "prompt": prompt,
            "allowed_tools": skill.metadata.allowed_tools,
            "model": skill.metadata.model,
            "effort": skill.metadata.effort,
            "context": skill.metadata.context,
            "agent": skill.metadata.agent,
            "source_path": str(skill.source_path) if skill.source_path else None,
        }

