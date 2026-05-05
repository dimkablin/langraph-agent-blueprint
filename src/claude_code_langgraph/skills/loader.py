"""Skill-system module for loading, parsing, registering, or invoking file-based assistant skills."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .base import SkillDefinition, SkillMetadata
from .frontmatter import parse_frontmatter


class SkillLoader:
    """Loads file-based skills from `skill-name/SKILL.md` directories."""

    def load_skill_dir(self, skill_dir: str | Path) -> SkillDefinition:
        directory = Path(skill_dir)
        skill_path = directory / "SKILL.md"
        if not skill_path.exists():
            raise FileNotFoundError(skill_path)
        text = skill_path.read_text(encoding="utf-8")
        metadata_raw, body = parse_frontmatter(text)
        if "name" not in metadata_raw:
            metadata_raw["name"] = directory.name
        if "description" not in metadata_raw:
            metadata_raw["description"] = body.strip().splitlines()[0] if body.strip() else directory.name
        try:
            metadata = SkillMetadata.model_validate(metadata_raw)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        references = [path for path in directory.iterdir() if path.name != "SKILL.md"]
        return SkillDefinition(metadata=metadata, prompt_template=body, source_path=skill_path, references=references)

    def load_root(self, root: str | Path) -> list[SkillDefinition]:
        base = Path(root)
        if not base.exists():
            return []
        skills: list[SkillDefinition] = []
        for skill_dir in base.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append(self.load_skill_dir(skill_dir))
        return skills

