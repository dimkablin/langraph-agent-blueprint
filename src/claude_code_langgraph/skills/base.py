"""Core skill metadata and definition models parsed from SKILL.md files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SkillMetadata(BaseModel):
    """Metadata parsed from SKILL.md frontmatter."""

    name: str
    description: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    model: str | None = None
    effort: str | None = None
    hooks: list[str] = Field(default_factory=list)
    context: str = "current"
    agent: str | None = None
    paths: list[str] = Field(default_factory=list)
    shell: bool = False
    enabled: bool = True
    feature_gate: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_string(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("skill name must be a non-empty string")
        return value.strip()


class SkillDefinition(BaseModel):
    """Loaded prompt-driven capability."""

    metadata: SkillMetadata
    prompt_template: str
    source_path: Path | None = None
    references: list[Path] = Field(default_factory=list)

    def render(self, args: str = "", state: dict[str, Any] | None = None) -> str:
        rendered = self.prompt_template.replace("{{args}}", args)
        rendered = rendered.replace("$ARGUMENTS", args)
        return rendered

