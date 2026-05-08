"""Pydantic boundary models for eval/replay scenarios and reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from langgraph_agent_blueprint.models.base import FrozenRuntimeModel, RuntimeModel


class EvalInput(FrozenRuntimeModel):
    """One graph input turn plus optional permission resume behavior."""

    text: str
    approve: bool | None = None
    resume_payload: dict[str, Any] | None = None


class ExpectedEvent(FrozenRuntimeModel):
    type: str
    contains: dict[str, Any] = Field(default_factory=dict)
    min_count: int = Field(default=1, ge=0)
    max_count: int | None = Field(default=None, ge=0)


class ExpectedToolCall(FrozenRuntimeModel):
    name: str
    status: Literal["ok", "error", "rejected", "disabled", "unavailable", "any"] = "any"
    min_count: int = Field(default=1, ge=0)


class ExpectedSkillInvocation(FrozenRuntimeModel):
    name: str
    min_count: int = Field(default=1, ge=0)


class ExpectedPermissionRequest(FrozenRuntimeModel):
    tool_name: str | None = None
    decision: Literal["required", "approved", "rejected", "any"] = "any"


class ExpectedMCPCall(FrozenRuntimeModel):
    server_name: str
    tool_name: str
    status: Literal["ok", "error", "rejected", "any"] = "any"


class ExpectedSubagentRun(FrozenRuntimeModel):
    status: Literal["ok", "error", "timeout", "any"] = "any"
    min_count: int = Field(default=1, ge=0)


class ExpectedContextFragment(FrozenRuntimeModel):
    kind: str | None = None
    title_contains: str | None = None
    content_contains: str | None = None
    trust: str | None = None


class ExpectedFinalResponse(FrozenRuntimeModel):
    contains: list[str] = Field(default_factory=list)
    not_contains: list[str] = Field(default_factory=list)


class ExpectedFileState(FrozenRuntimeModel):
    path: str
    exists: bool = True
    contains: list[str] = Field(default_factory=list)
    not_contains: list[str] = Field(default_factory=list)


class EvalExpectations(FrozenRuntimeModel):
    events: list[ExpectedEvent] = Field(default_factory=list)
    tool_calls: list[ExpectedToolCall] = Field(default_factory=list)
    skills: list[ExpectedSkillInvocation] = Field(default_factory=list)
    permissions: list[ExpectedPermissionRequest] = Field(default_factory=list)
    mcp_calls: list[ExpectedMCPCall] = Field(default_factory=list)
    subagents: list[ExpectedSubagentRun] = Field(default_factory=list)
    context_fragments: list[ExpectedContextFragment] = Field(default_factory=list)
    files: list[ExpectedFileState] = Field(default_factory=list)
    final_response: ExpectedFinalResponse | None = None


class EvalStep(FrozenRuntimeModel):
    input: EvalInput
    expect: EvalExpectations = Field(default_factory=EvalExpectations)


class EvalScenario(FrozenRuntimeModel):
    id: str
    description: str
    provider: str = "fake"
    workspace_fixture: str | None = None
    mcp_fixture: str | None = None
    plugin_fixtures: list[str] = Field(default_factory=list)
    steps: list[EvalStep]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("steps")
    @classmethod
    def _steps_must_not_be_empty(cls, value: list[EvalStep]) -> list[EvalStep]:
        if not value:
            raise ValueError("eval scenario must include at least one step")
        return value


class EvalRunResult(RuntimeModel):
    scenario_id: str
    passed: bool
    failures: list[str] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    final_state: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalReport(RuntimeModel):
    run_id: str
    passed: bool
    results: list[EvalRunResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
