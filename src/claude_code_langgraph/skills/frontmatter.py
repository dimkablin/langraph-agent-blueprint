from __future__ import annotations

from typing import Any

import yaml


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from SKILL.md."""

    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata_raw = parts[1]
    body = parts[2].lstrip("\r\n")
    metadata = yaml.safe_load(metadata_raw) or {}
    if not isinstance(metadata, dict):
        raise ValueError("Skill frontmatter must be a mapping")
    return metadata, body

