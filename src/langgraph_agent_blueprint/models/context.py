"""Typed context-provider and attachment boundary models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from langgraph_agent_blueprint.models.base import FrozenRuntimeModel


ContextRefKind = Literal[
    "file",
    "directory",
    "glob",
    "notebook",
    "mcp_resource",
    "url",
    "text",
    "image",
    "pdf",
    "unknown",
]
TrustLevel = Literal["trusted_local", "untrusted_external", "plugin_provided", "mcp_external", "user_provided"]


class ContextReference(FrozenRuntimeModel):
    """Reference extracted from user/API/plugin input before provider resolution."""

    kind: ContextRefKind
    value: str
    label: str | None = None
    source: Literal["user_input", "api_attachment", "cli_attachment", "plugin", "mcp"] = "user_input"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttachmentRef(FrozenRuntimeModel):
    """Serializable attachment metadata accepted by CLI/API/future frontend."""

    id: str
    kind: ContextRefKind
    name: str | None = None
    uri: str | None = None
    path: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    trust: TrustLevel = "user_provided"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttachmentContent(FrozenRuntimeModel):
    """Resolved attachment content or safe placeholder summary."""

    ref_id: str
    kind: ContextRefKind
    text: str | None = None
    summary: str | None = None
    mime_type: str | None = None
    truncated: bool = False
    trust: TrustLevel
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextFragment(FrozenRuntimeModel):
    """Model-facing context fragment after provider resolution and budget application."""

    id: str
    kind: ContextRefKind
    title: str
    content: str
    trust: TrustLevel
    source_ref: dict[str, Any] = Field(default_factory=dict)
    token_estimate: int = 0
    truncated: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextBudgetReport(FrozenRuntimeModel):
    """Summary of context budget inclusion, truncation, and drops."""

    max_tokens: int
    used_tokens: int
    dropped: list[dict[str, Any]] = Field(default_factory=list)
    truncated: list[dict[str, Any]] = Field(default_factory=list)
    included: list[str] = Field(default_factory=list)


class ResolvedContextItem(FrozenRuntimeModel):
    """Provider result for one reference or attachment."""

    reference: ContextReference
    fragments: list[ContextFragment] = Field(default_factory=list)
    attachments: list[AttachmentContent] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
