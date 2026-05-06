"""Typed plugin boundary models for external plugin discovery and installation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from .base import FrozenRuntimeModel


class PluginSource(FrozenRuntimeModel):
    """Normalized user/config plugin source reference."""

    name: str
    source: str
    ref: str | None = None
    enabled: bool = True


class PluginManifest(FrozenRuntimeModel):
    """Validated plugin metadata parsed from harness-specific manifests."""

    model_config = ConfigDict(extra="ignore", frozen=True, arbitrary_types_allowed=True)

    name: str
    version: str | None = None
    description: str | None = None
    author: dict[str, Any] | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    skills_path: str | None = None
    bootstrap_skill: str | None = None


class PluginContribution(FrozenRuntimeModel):
    """Resolved plugin contribution safe to put in graph state."""

    plugin_name: str
    root_path: str
    manifest: PluginManifest
    skills_path: str | None = None
    bootstrap_skill: str | None = None
    system_context_fragments: list[str] = Field(default_factory=list)


class PluginInstallResult(FrozenRuntimeModel):
    """Result of an explicit plugin install/update/remove operation."""

    plugin_name: str | None = None
    status: Literal["installed", "updated", "removed", "not_found", "error"]
    message: str
    root_path: str | None = None
    lock_path: str | None = None
    source: PluginSource | None = None
    manifest: PluginManifest | None = None
    resolved_commit: str | None = None
