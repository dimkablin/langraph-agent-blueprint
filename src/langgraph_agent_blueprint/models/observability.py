"""Pydantic boundary models for optional Langfuse observability."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from langgraph_agent_blueprint.models.base import FrozenRuntimeModel, RuntimeModel


class LangfuseConfig(RuntimeModel):
    """Langfuse configuration loaded from env/config without exposing secrets."""

    enabled: bool = False
    public_key: str | None = None
    secret_key: str | None = None
    base_url: str | None = None
    environment: str = "dev"
    release: str | None = None
    trace_user_id: str | None = None
    debug: bool = False
    capture_inputs: bool = True
    capture_outputs: bool = True
    include_project_paths: bool = False
    max_event_chars: int = 4000

    def redacted(self) -> dict[str, Any]:
        """Return a status/config view safe for commands, events, and logs."""

        data = self.model_dump(mode="json")
        for key in ("public_key", "secret_key"):
            data[key] = "***" if data.get(key) else None
        return data


class TraceContext(FrozenRuntimeModel):
    """JSON-safe trace context used to build graph invocation callback config."""

    session_id: str
    thread_id: str | None = None
    project_root: str | None = None
    run_id: str | None = None
    user_id: str | None = None
    environment: str = "dev"
    release: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceMetadata(FrozenRuntimeModel):
    """Trace metadata that describes the current runtime turn."""

    provider: str | None = None
    model: str | None = None
    command: str | None = None
    active_skill: str | None = None
    active_tool: str | None = None
    plugin_names: list[str] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)
    permission_mode: str | None = None
    graph_node: str | None = None


class ObservabilityEvent(FrozenRuntimeModel):
    """Normalized event payload before it is sent to an observability backend."""

    type: str
    name: str
    session_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    severity: Literal["info", "warning", "error"] = "info"
