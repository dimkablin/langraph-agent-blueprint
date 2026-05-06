"""Skill invocation service that validates skill args and renders prompt templates."""

from __future__ import annotations

from typing import Any

from .args import format_skill_args_for_prompt, validate_skill_args
from .registry import SkillRegistry


class SkillInvocationService:
    """Resolves, renders, and records skill invocations."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def invoke(self, name: str, args: Any, state: dict[str, Any]) -> dict[str, Any]:
        """Resolve a skill, render its prompt with arguments, and return invocation metadata."""

        skill = self.registry.get(name)
        typed_args = validate_skill_args(name, args, skill.args_schema)
        formatted_args = format_skill_args_for_prompt(name, typed_args)
        prompt = skill.render(formatted_args, state)
        return {
            "name": skill.metadata.name,
            "requested_name": name,
            "args": formatted_args,
            "typed_args": typed_args.model_dump(mode="json"),
            "args_schema": skill.args_schema.__name__,
            "prompt": prompt,
            "allowed_tools": skill.metadata.allowed_tools,
            "model": skill.metadata.model,
            "effort": skill.metadata.effort,
            "context": skill.metadata.context,
            "agent": skill.metadata.agent,
            "source_path": str(skill.source_path) if skill.source_path else None,
        }
