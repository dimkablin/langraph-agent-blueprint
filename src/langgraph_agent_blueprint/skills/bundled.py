"""Skill-system module for loading, parsing, registering, or invoking file-based assistant skills."""

from __future__ import annotations

from pathlib import Path

from .args import args_schema_for_skill
from .loader import SkillLoader


BUILTIN_SKILLS = ["batch", "debug", "remember", "simplify", "skillify", "stuck", "update-config", "verify"]
OPTIONAL_SKILLS = ["loop", "schedule", "keybindings-help", "lorem-ipsum", "claude-api", "claude-api-content", "claude-in-chrome"]


def bundled_skills_root() -> Path:
    return Path(__file__).parent / "definitions"


def load_bundled_skills() -> list:
    loader = SkillLoader()
    skills = []
    for name in BUILTIN_SKILLS:
        skill = loader.load_skill_dir(bundled_skills_root() / name)
        skills.append(skill.model_copy(update={"args_schema": args_schema_for_skill(name)}))
    return skills

