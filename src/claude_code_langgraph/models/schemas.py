from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApprovalDecision(BaseModel):
    """Human decision for a pending permission request."""

    approved: bool
    reason: str | None = None
    persist_rule: bool = False


class PluginManifest(BaseModel):
    """Minimal plugin manifest accepted by the plugin service."""

    name: str
    commands: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    hooks: list[dict[str, Any]] = Field(default_factory=list)
    mcp: dict[str, Any] = Field(default_factory=dict)

