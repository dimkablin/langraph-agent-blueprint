"""Typed plugin boundary models for external plugin discovery and installation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from .base import FrozenRuntimeModel
from .hooks import HookContribution


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
    hooks: list[dict[str, Any]] = Field(default_factory=list)
    policies: list[dict[str, Any]] = Field(default_factory=list)


class PluginPolicyContribution(FrozenRuntimeModel):
    """Declarative plugin runtime policy contribution."""

    id: str
    plugin_name: str | None = None
    priority: int = 100
    enabled: bool = True
    policy_type: Literal["skill_activation", "context", "none"] = "skill_activation"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PluginPolicyContext(FrozenRuntimeModel):
    """Read-only context passed to plugin policy evaluators."""

    session_id: str
    input_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    invoked_skills: list[str] = Field(default_factory=list)


class PluginPolicyResult(FrozenRuntimeModel):
    """Controlled result returned by plugin policy evaluation."""

    contribution_id: str
    plugin_name: str | None = None
    action: Literal["activate_skill", "continue", "block", "error"] = "continue"
    skill_name: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PluginContribution(FrozenRuntimeModel):
    """Resolved plugin contribution safe to put in graph state."""

    plugin_name: str
    root_path: str
    manifest: PluginManifest
    skills_path: str | None = None
    bootstrap_skill: str | None = None
    system_context_fragments: list[str] = Field(default_factory=list)
    hooks: list[HookContribution] = Field(default_factory=list)
    hook_warnings: list[dict[str, str]] = Field(default_factory=list)
    policies: list[PluginPolicyContribution] = Field(default_factory=list)
    policy_warnings: list[dict[str, str]] = Field(default_factory=list)


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
