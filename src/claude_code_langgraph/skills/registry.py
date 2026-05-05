"""SkillRegistry implementation for bundled, file-based, plugin, and MCP skills."""

from __future__ import annotations

from pathlib import Path

from .base import SkillDefinition
from .bundled import load_bundled_skills
from .loader import SkillLoader


class SkillRegistry:
    """Registry for bundled, file-based, plugin, and MCP skills."""

    def __init__(self, loader: SkillLoader | None = None) -> None:
        self.loader = loader or SkillLoader()
        self._skills: dict[str, SkillDefinition] = {}
        self.disabled: dict[str, str] = {}

    def register(self, skill: SkillDefinition) -> None:
        self._skills[skill.metadata.name] = skill

    def get(self, name: str) -> SkillDefinition:
        if name not in self._skills:
            raise KeyError(f"Unknown skill: {name}")
        return self._skills[name]

    def all(self) -> dict[str, SkillDefinition]:
        return dict(self._skills)

    def load_from_paths(self, roots: list[str | Path]) -> None:
        for root in roots:
            for skill in self.loader.load_root(root):
                if skill.metadata.enabled:
                    self.register(skill)
                else:
                    self.disabled[skill.metadata.name] = "disabled by metadata"

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {name: skill.metadata.model_dump(mode="json") for name, skill in self._skills.items()}


def build_builtin_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for skill in load_bundled_skills():
        registry.register(skill)
    for name in ["loop", "schedule", "keybindings-help", "lorem-ipsum", "claude-api", "claude-api-content", "claude-in-chrome"]:
        registry.disabled[name] = "optional skill is documented but disabled in the initial Python port"
    return registry

