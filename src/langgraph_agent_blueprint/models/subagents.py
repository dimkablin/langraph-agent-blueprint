"""Typed boundary models for real subagent child graph runs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from langgraph_agent_blueprint.models.base import FrozenRuntimeModel
from langgraph_agent_blueprint.utils.ids import validate_runtime_id, validate_session_id, validate_thread_id


ChildRunStatus = Literal["running", "completed", "failed", "cancelled", "timeout"]
SubagentResultStatus = Literal["ok", "error", "cancelled", "timeout"]


class SubagentRequest(FrozenRuntimeModel):
    """Validated request payload accepted by the model-callable agent tool."""

    prompt: str
    name: str | None = None
    purpose: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    max_turns: int = Field(default=8, ge=1, le=100)
    timeout_seconds: float | None = Field(default=300.0)
    inherit_memory: bool = True
    inherit_todos: bool = False
    inherit_context: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt")
    @classmethod
    def _prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("subagent prompt must not be empty")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def _timeout_must_be_positive(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return value


class ChildRunMetadata(FrozenRuntimeModel):
    """Parent/child identity and lifecycle metadata for a child graph run."""

    child_run_id: str
    parent_session_id: str
    parent_thread_id: str
    child_session_id: str
    child_thread_id: str
    name: str | None = None
    purpose: str | None = None
    status: ChildRunStatus
    started_at: str
    completed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("child_run_id")
    @classmethod
    def _child_run_id_must_be_safe(cls, value: str) -> str:
        return validate_runtime_id(value, kind="child_run_id")

    @field_validator("parent_session_id", "child_session_id")
    @classmethod
    def _session_ids_must_be_safe(cls, value: str) -> str:
        return validate_session_id(value)

    @field_validator("parent_thread_id", "child_thread_id")
    @classmethod
    def _thread_ids_must_be_safe(cls, value: str) -> str:
        return validate_thread_id(value)


class SubagentResult(FrozenRuntimeModel):
    """Controlled result merged back from a child graph run into the parent."""

    child_run_id: str
    status: SubagentResultStatus
    summary: str
    final_response: str | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResultMergePolicy(FrozenRuntimeModel):
    """Policy toggles controlling how much child output enters parent state."""

    include_summary_in_parent: bool = True
    include_artifacts: bool = True
    include_tool_results: bool = False
    include_child_messages: bool = False
