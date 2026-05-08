"""SkillRegistry implementation for bundled, file-based, plugin, and MCP skills."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.models import PluginContribution

from .base import SkillDefinition
from .bundled import load_bundled_skills
from .loader import SkillLoader


class SkillRegistry:
    """Registry for bundled, file-based, plugin, and MCP skills."""

    def __init__(self, loader: SkillLoader | None = None) -> None:
        self.loader = loader or SkillLoader()
        self._skills: dict[str, SkillDefinition] = {}
        self._aliases: dict[str, str] = {}
        self.disabled: dict[str, str] = {}

    def register(self, skill: SkillDefinition, aliases: list[str] | None = None) -> None:
        self._skills[skill.metadata.name] = skill
        if skill.metadata.plugin_name is None:
            self._aliases.pop(skill.metadata.name, None)
        for alias in aliases or []:
            if alias not in self._skills:
                self._aliases[alias] = skill.metadata.name

    def get(self, name: str) -> SkillDefinition:
        resolved = self._aliases.get(name, name)
        if resolved not in self._skills:
            raise KeyError(f"Unknown skill: {name}")
        return self._skills[resolved]

    def all(self) -> dict[str, SkillDefinition]:
        return dict(self._skills)

    def load_from_paths(self, roots: list[str | Path]) -> None:
        """Load configured skill roots and split enabled skills from disabled definitions."""

        for root in roots:
            for skill in self.loader.load_root(root):
                if skill.metadata.enabled:
                    self.register(skill)
                else:
                    self.disabled[skill.metadata.name] = "disabled by metadata"

    def load_plugin_contributions(self, contributions: list[PluginContribution]) -> None:
        """Load plugin skills with a stable `<plugin>/<skill>` registry namespace."""

        for contribution in contributions:
            if not contribution.skills_path:
                continue
            for skill in self.loader.load_root(contribution.skills_path):
                original_name = skill.metadata.name
                registry_name = f"{contribution.plugin_name}/{original_name}"
                metadata = skill.metadata.model_copy(
                    update={
                        "name": registry_name,
                        "original_name": original_name,
                        "plugin_name": contribution.plugin_name,
                        "source_type": "plugin",
                        "priority": 50,
                    }
                )
                plugin_skill = skill.model_copy(update={"metadata": metadata})
                if plugin_skill.metadata.enabled:
                    self.register(plugin_skill, aliases=[original_name])
                else:
                    self.disabled[registry_name] = "disabled by metadata"

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {name: skill.metadata.model_dump(mode="json") for name, skill in self._skills.items()}


def build_builtin_skill_registry() -> SkillRegistry:
    """Register bundled skills and record optional audited skills as disabled."""

    registry = SkillRegistry()
    for skill in load_bundled_skills():
        registry.register(skill)
    for name in ["loop", "schedule", "keybindings-help", "lorem-ipsum", "claude-api", "claude-api-content", "claude-in-chrome"]:
        registry.disabled[name] = "optional skill is documented but disabled in the initial Python port"
    return registry

