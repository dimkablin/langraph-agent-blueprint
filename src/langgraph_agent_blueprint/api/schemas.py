"""Pydantic DTOs for FastAPI chat, approval, streaming, and frontend status payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

from langgraph_agent_blueprint.models import (
    AttachmentRef,
    ConfigDiagnostic,
    ConfigSource,
    ConfigValueOrigin,
    PermissionRequest,
)
from langgraph_agent_blueprint.utils.ids import validate_session_id, validate_thread_id

ModelIntelligenceLevel = Literal["low", "medium", "high", "very_high"]
PermissionMode = Literal["default", "accept_edits", "bypass_read_only", "plan", "strict"]


class RuntimeEventDTO(BaseModel):
    """Stable frontend event envelope emitted by graph runtime adapters."""

    id: str
    type: str
    timestamp: datetime
    session_id: str
    node: str | None = None
    severity: Literal["info", "warning", "error"] = "info"
    data: dict[str, Any] = Field(default_factory=dict)


class StreamFrame(BaseModel):
    """One SSE data frame from the live chat stream."""

    type: Literal["event", "done", "error"]
    event: RuntimeEventDTO | None = None
    session_id: str | None = None
    thread_id: str | None = None
    final_response: str | None = None
    error: str | None = None


class ChatRequest(BaseModel):
    """API request payload for starting or continuing a graph-backed chat turn."""

    message: str
    project_id: str | None = None
    session_id: str | None = None
    thread_id: str | None = None
    model_intelligence: ModelIntelligenceLevel | None = None
    permission_mode: PermissionMode | None = None
    attachments: list[AttachmentRef] = Field(default_factory=list)

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str | None) -> str | None:
        return validate_session_id(value) if value is not None else None

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, value: str | None) -> str | None:
        return validate_thread_id(value) if value is not None else None


class ChatResponse(BaseModel):
    """API response payload containing session ids, final text, events, and pending approvals."""

    session_id: str
    thread_id: str
    final_response: str | None = None
    events: list[RuntimeEventDTO]
    usage: dict[str, Any] = Field(default_factory=dict)
    permission_required: PermissionRequest | None = None


class ChatCancelRequest(BaseModel):
    """API request payload for stopping an active streaming graph turn."""

    thread_id: str
    session_id: str | None = None
    reason: str | None = None

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str | None) -> str | None:
        return validate_session_id(value) if value is not None else None

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, value: str) -> str:
        return validate_thread_id(value)


class ChatCancelResponse(BaseModel):
    """API response payload returned after a stop-generation request."""

    cancelled: bool
    thread_id: str
    session_id: str | None = None
    reason: str | None = None


class WorkspaceAddRequest(BaseModel):
    """Request to register and select a validated local workspace root."""

    root_path: str


class WorkspaceSelectRequest(BaseModel):
    """Request to make an existing workspace the active workspace."""

    project_id: str


class WorkspaceCheckoutRequest(BaseModel):
    """Request to checkout an existing local branch in a workspace."""

    branch: str
    confirm_dirty: bool = False


class PermissionDecisionDTO(BaseModel):
    """Explicit frontend approval/rejection decision for one pending tool call."""

    tool_call_id: str
    decision: Literal["approved", "rejected"]
    reason: str | None = None
    remember: bool = False


class LegacyPermissionDecisionDTO(BaseModel):
    """Backwards-compatible approval shape used by the initial React CLI shell."""

    approved: bool
    reason: str | None = None
    remember: bool = False


class ApprovalRequest(BaseModel):
    """API request payload used to resume an interrupted graph with a human permission decision."""

    thread_id: str
    session_id: str | None = None
    decision: PermissionDecisionDTO | LegacyPermissionDecisionDTO

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str | None) -> str | None:
        return validate_session_id(value) if value is not None else None

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, value: str) -> str:
        return validate_thread_id(value)

    def decision_payload(self) -> dict[str, Any]:
        """Return the graph resume payload while preserving legacy approved-bool support."""

        return self.decision.model_dump(mode="json", exclude_none=True)


class RegistryItemDTO(BaseModel):
    """Common frontend metadata row for commands, skills, tools, and extension registries."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    type: str | None = None
    status: str | None = None
    plugin_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandRegistryDTO(RootModel[dict[str, RegistryItemDTO]]):
    """Slash-command registry response keyed by command name for backwards compatibility."""


class SkillRegistryDTO(RootModel[dict[str, RegistryItemDTO]]):
    """Skill registry response keyed by skill name for backwards compatibility."""


class ToolRegistryDTO(RootModel[dict[str, RegistryItemDTO]]):
    """Tool registry response keyed by model-callable tool name for backwards compatibility."""


class MessageDTO(BaseModel):
    """Frontend-safe normalized chat/session message."""

    id: str
    role: str
    content: str
    type: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_call_id: str | None = None


class ToolCallRecordDTO(BaseModel):
    """Frontend-safe tool execution record from session persistence."""

    id: str
    name: str
    status: str
    content: str = ""
    output_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | str | None = None


class ContextStateDTO(BaseModel):
    """Resolved context state for a session side panel."""

    references: list[dict[str, Any]] = Field(default_factory=list)
    fragments: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ChildRunListItemDTO(BaseModel):
    """Summary row for one persisted child/subagent run."""

    child_run_id: str
    parent_session_id: str | None = None
    child_session_id: str | None = None
    child_thread_id: str | None = None
    name: str | None = None
    purpose: str | None = None
    status: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    summary: str | None = None


class ChildRunDetailDTO(BaseModel):
    """Frontend-safe child/subagent run detail."""

    metadata: dict[str, Any]
    result: dict[str, Any] = Field(default_factory=dict)
    events: list[RuntimeEventDTO] = Field(default_factory=list)


class SessionListItemDTO(BaseModel):
    """Frontend session list item with counts instead of raw storage shape."""

    session_id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    provider: str | None = None
    model: str | None = None
    message_count: int = 0
    event_count: int = 0
    tool_call_count: int = 0
    child_run_count: int = 0
    usage: dict[str, Any] = Field(default_factory=dict)


class SessionDetailDTO(BaseModel):
    """Frontend-safe session detail DTO."""

    session_id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    provider: str | None = None
    model: str | None = None
    messages: list[MessageDTO] = Field(default_factory=list)
    events: list[RuntimeEventDTO] = Field(default_factory=list)
    tool_calls: list[ToolCallRecordDTO] = Field(default_factory=list)
    todos: list[dict[str, Any]] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    context: ContextStateDTO = Field(default_factory=ContextStateDTO)
    child_runs: list[ChildRunListItemDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    """Request body for session transcript export."""

    format: Literal["markdown", "text"] = "markdown"


class ExportRecordDTO(BaseModel):
    """Frontend-safe export result."""

    session_id: str
    format: str
    path: str
    bytes: int


class ConfigShowDTO(BaseModel):
    """Redacted effective config for read-only frontend display."""

    values: dict[str, Any]


class ConfigExplainDTO(BaseModel):
    """Config source and value-origin explanation."""

    sources: list[ConfigSource] = Field(default_factory=list)
    values: list[ConfigValueOrigin] = Field(default_factory=list)
    diagnostics: list[ConfigDiagnostic] = Field(default_factory=list)


class ConfigValidateDTO(BaseModel):
    """Config validation diagnostics."""

    ok: bool
    diagnostics: list[ConfigDiagnostic] = Field(default_factory=list)


class PluginStatusDTO(BaseModel):
    """Read-only plugin status and diagnostics."""

    plugins: list[dict[str, Any]] = Field(default_factory=list)
    contributions: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)


class HookStatusDTO(BaseModel):
    """Read-only hook registry status."""

    hooks: list[dict[str, Any]] = Field(default_factory=list)


class MCPStatusDTO(BaseModel):
    """Read-only MCP discovery/status snapshot."""

    servers: list[dict[str, Any]] = Field(default_factory=list)
    tools: dict[str, dict[str, Any]] = Field(default_factory=dict)
    resources: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    prompts: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    transport_support: dict[str, bool] = Field(default_factory=dict)
    invalid_servers: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ObservabilityStatusDTO(BaseModel):
    """Read-only observability backend status."""

    enabled: bool
    mode: str
    sdk_installed: bool | None = None
    base_url_configured: bool = False
    public_key_present: bool = False
    secret_key_present: bool = False
    environment: str | None = None
    release: str | None = None
    capture_inputs: bool = False
    capture_outputs: bool = False
    runtime_events_mode: str | None = None
    auth_check: str | None = None
    last_error: str | None = None
