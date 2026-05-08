"""Pydantic models for config layering explanations and diagnostics."""

from __future__ import annotations

from typing import Literal

from langgraph_agent_blueprint.models.base import FrozenRuntimeModel


class ConfigSource(FrozenRuntimeModel):
    """One config source considered by the loader."""

    name: str
    kind: Literal["defaults", "dotenv", "user_config", "project_config", "env", "cli", "override"]
    path: str | None = None
    loaded: bool = False
    error: str | None = None


class ConfigValueOrigin(FrozenRuntimeModel):
    """Effective redacted value plus the source layer that supplied it."""

    key: str
    value_repr: str
    source: str
    redacted: bool = False


class ConfigDiagnostic(FrozenRuntimeModel):
    """Validation/explain diagnostic for one config key or source."""

    key: str
    status: Literal["ok", "warning", "error"]
    message: str
    source: str | None = None


class EffectiveConfigReport(FrozenRuntimeModel):
    """Complete explain report for effective config."""

    sources: list[ConfigSource]
    values: list[ConfigValueOrigin]
    diagnostics: list[ConfigDiagnostic]
