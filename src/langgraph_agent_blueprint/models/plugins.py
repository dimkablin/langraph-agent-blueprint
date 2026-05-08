"""Typed plugin boundary models for external plugin discovery and installation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from .base import FrozenRuntimeModel
from .hooks import HookContribution
from .tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata


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
    commands: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    mcp_servers: dict[str, Any] = Field(default_factory=dict)
    context_providers: list[dict[str, Any]] = Field(default_factory=list)
    bootstrap: dict[str, Any] = Field(default_factory=dict)
    trust: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PluginTrustPolicy(FrozenRuntimeModel):
    """Conservative trust metadata for plugin contributions."""

    level: Literal["trusted", "untrusted"] = "untrusted"
    allow_mcp_servers: bool = False
    allow_executable_code: bool = False
    reason: str | None = None


class PluginSDKDiagnostic(FrozenRuntimeModel):
    """Structured warning/error produced while parsing plugin SDK contributions."""

    plugin_name: str
    contribution_type: str
    name: str | None = None
    severity: Literal["warning", "error"] = "warning"
    message: str


class PluginCommandContribution(FrozenRuntimeModel):
    """Declarative plugin slash-command contribution."""

    plugin_name: str
    name: str
    command_type: Literal["static_response", "prompt", "skill"]
    description: str | None = None
    response: str | None = None
    prompt: str | None = None
    skill: str | None = None
    enabled: bool = True
    registry_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _fill_registry_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("registry_name") and data.get("name"):
            data = dict(data)
            data["registry_name"] = str(data["name"]).strip().lower()
        return data

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("plugin command name must not be empty")
        return value.strip().lower()


class PluginToolContribution(FrozenRuntimeModel):
    """Declarative plugin tool contribution."""

    plugin_name: str
    name: str
    kind: Literal["static_text", "context_lookup", "disabled_placeholder"] = "static_text"
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})
    response: str | None = None
    path: str | None = None
    enabled: bool = True
    registry_name: str | None = None
    permission: ToolPermissionMetadata = Field(
        default_factory=lambda: ToolPermissionMetadata(
            action="read",
            risk="low",
            is_read_only=True,
            allowed_in_plan_mode=True,
            external=True,
        )
    )
    runtime: ToolRuntimeMetadata = Field(default_factory=lambda: ToolRuntimeMetadata(kind="plugin", route="execute"))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _fill_tool_registry_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("registry_name") and data.get("plugin_name") and data.get("name"):
            data = dict(data)
            data["registry_name"] = f"plugin.{data['plugin_name']}.{data['name']}"
        return data

    @field_validator("name")
    @classmethod
    def _tool_name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("plugin tool name must not be empty")
        return value.strip()


class PluginMCPContribution(FrozenRuntimeModel):
    """Plugin-contributed MCP server config."""

    plugin_name: str
    server_name: str
    registry_name: str
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PluginContextProviderContribution(FrozenRuntimeModel):
    """Declarative plugin context provider contribution."""

    plugin_name: str
    name: str
    kind: Literal["static", "plugin_file", "alias"] = "static"
    description: str | None = None
    content: str | None = None
    path: str | None = None
    target: str | None = None
    root_path: str | None = None
    enabled: bool = True
    trust: Literal["plugin_provided"] = "plugin_provided"
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    enabled: bool = True
    disabled_reason: str | None = None
    trust: PluginTrustPolicy = Field(default_factory=PluginTrustPolicy)
    system_context_fragments: list[str] = Field(default_factory=list)
    hooks: list[HookContribution] = Field(default_factory=list)
    hook_warnings: list[dict[str, str]] = Field(default_factory=list)
    policies: list[PluginPolicyContribution] = Field(default_factory=list)
    policy_warnings: list[dict[str, str]] = Field(default_factory=list)
    commands: list[PluginCommandContribution] = Field(default_factory=list)
    command_warnings: list[dict[str, str]] = Field(default_factory=list)
    tools: list[PluginToolContribution] = Field(default_factory=list)
    tool_warnings: list[dict[str, str]] = Field(default_factory=list)
    mcp_servers: list[PluginMCPContribution] = Field(default_factory=list)
    mcp_warnings: list[dict[str, str]] = Field(default_factory=list)
    context_providers: list[PluginContextProviderContribution] = Field(default_factory=list)
    context_warnings: list[dict[str, str]] = Field(default_factory=list)
    sdk_warnings: list[PluginSDKDiagnostic] = Field(default_factory=list)


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
