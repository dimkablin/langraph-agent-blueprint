"""Pydantic boundary models for the MCP client runtime."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base import FrozenRuntimeModel, RuntimeModel


MCPTransportKind = Literal["stdio", "streamable_http"]

MCPServerStatus = Literal[
    "configured",
    "starting",
    "connected",
    "failed",
    "disabled",
    "stopped",
]


class MCPStdioConfig(FrozenRuntimeModel):
    """Configuration for an explicitly configured local stdio MCP server."""

    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None


class MCPHttpConfig(FrozenRuntimeModel):
    """Configuration placeholder for Streamable HTTP MCP servers."""

    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float = 30.0


class MCPServerConfig(FrozenRuntimeModel):
    """Validated config for one MCP server."""

    name: str
    enabled: bool = True
    transport: MCPTransportKind
    stdio: MCPStdioConfig | None = None
    http: MCPHttpConfig | None = None
    timeout_seconds: float = 30.0
    trust_level: Literal["trusted", "untrusted"] = "untrusted"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_transport_config(self) -> "MCPServerConfig":
        if not self.enabled:
            return self
        if self.transport == "stdio" and self.stdio is None:
            raise ValueError("stdio MCP servers require stdio config")
        if self.transport == "streamable_http" and self.http is None:
            raise ValueError("streamable_http MCP servers require http config")
        return self


class MCPConnectionState(RuntimeModel):
    """Serializable state for one MCP client connection."""

    name: str
    status: MCPServerStatus
    transport: MCPTransportKind
    capabilities: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    pid: int | None = None


class MCPToolContribution(FrozenRuntimeModel):
    """Tool discovered from an MCP server and registered in ToolRegistry."""

    server_name: str
    tool_name: str
    registry_name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class MCPResourceContribution(FrozenRuntimeModel):
    """Resource discovered from an MCP server."""

    server_name: str
    uri: str
    name: str | None = None
    description: str | None = None
    mime_type: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class MCPPromptContribution(FrozenRuntimeModel):
    """Prompt discovered from an MCP server."""

    server_name: str
    prompt_name: str
    registry_name: str
    description: str | None = None
    arguments_schema: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallRequest(FrozenRuntimeModel):
    """Validated request to call an MCP server tool."""

    server_name: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResult(FrozenRuntimeModel):
    """Structured MCP tool call result returned to the graph tool path."""

    server_name: str
    tool_name: str
    status: Literal["ok", "error"]
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class MCPResourceReadResult(FrozenRuntimeModel):
    """Result of reading an MCP resource as untrusted external context."""

    server_name: str
    uri: str
    status: Literal["ok", "error"]
    content: str = ""
    mime_type: str | None = None
    external: bool = True
    untrusted: bool = True
    truncated: bool = False
    error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class MCPPromptGetResult(FrozenRuntimeModel):
    """Result of retrieving an MCP prompt as untrusted external prompt content."""

    server_name: str
    prompt_name: str
    status: Literal["ok", "error"]
    content: str = ""
    external: bool = True
    untrusted: bool = True
    error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
