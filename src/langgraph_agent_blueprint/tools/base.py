"""Base tool protocol, safety classes, shared output schema, and execution context."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models import (
    AgentActivityEvent,
    AgentActivityRef,
    AgentActivitySource,
    ToolActivitySpec,
    ToolPermissionMetadata,
    ToolRuntimeMetadata,
    ToolStateEffect,
)
from langgraph_agent_blueprint.utils.activity import activity_text_summary, normalize_activity_namespace, safe_activity_data


class ToolSafety(StrEnum):
    """Safety classification enum used by permission policy and tool metadata."""
    READ_ONLY = "read_only"
    WRITE = "write"
    SHELL = "shell"
    NETWORK = "network"
    MCP = "mcp"
    AGENT = "agent"
    SKILL = "skill"


class ToolOutput(BaseModel):
    """Common structured output payload returned by concrete tools."""
    ok: bool = True
    content: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecutionContext:
    """Runtime context passed to tools by the graph tool executor."""

    project_root: Path
    cwd: Path
    session_id: str = ""
    thread_id: str | None = None
    read_files: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    active_skill: Mapping[str, Any] | None = None


def freeze_context_value(value: Any) -> Any:
    """Return an immutable copy of JSON-like values exposed through tool context."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_context_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple, set)):
        return tuple(freeze_context_value(item) for item in value)
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseTool(Generic[InputT, OutputT]):
    """Base protocol for model-callable tools."""

    name: str
    description: str
    input_schema: type[InputT]
    output_schema: type[OutputT]
    permission: ToolPermissionMetadata = ToolPermissionMetadata(action="read", risk="low", is_read_only=True, allowed_in_plan_mode=True)
    runtime: ToolRuntimeMetadata = ToolRuntimeMetadata()
    timeout_seconds: float | None = None
    output_limit: int = 12000
    activity: ToolActivitySpec | None = None

    @property
    def safety(self) -> str:
        return self.permission.action

    @property
    def is_read_only(self) -> bool:
        return self.permission.is_read_only

    @property
    def requires_permission(self) -> bool:
        return self.permission.requires_permission

    def parse_input(self, data: dict[str, object]) -> InputT:
        return self.input_schema.model_validate(data)

    def run(self, data: InputT, context: ToolExecutionContext) -> OutputT:
        raise NotImplementedError

    async def arun(self, data: InputT, context: ToolExecutionContext) -> OutputT:
        return self.run(data, context)

    def activity_spec(self) -> ToolActivitySpec:
        """Return producer-owned activity metadata for this tool."""

        if self.activity is not None:
            return self.activity
        namespace = normalize_activity_namespace(self.name)
        display_name = self.description.split(".", 1)[0].strip() or self.name
        return ToolActivitySpec(
            display_name=display_name,
            started_type=f"tool.{namespace}.started",
            completed_type=f"tool.{namespace}.completed",
            failed_type=f"tool.{namespace}.failed",
            blocked_type=f"tool.{namespace}.blocked",
        )

    def build_activity_started_event(
        self,
        *,
        tool_call: Any,
        data: InputT | None,
        context: ToolExecutionContext,
    ) -> AgentActivityEvent:
        spec = self.activity_spec()
        payload = {
            "tool_call_id": getattr(tool_call, "id", None),
            "tool_name": self.name,
            **self.activity_started_data(data, context),
        }
        return AgentActivityEvent(
            id=f"activity_{getattr(tool_call, 'id', self.name)}_started",
            type=spec.started_type,
            source=self._activity_source(),
            category=self.activity_category(data=data, output=None, error=None),
            status="running",
            title=f"{spec.display_name} started",
            summary=self.activity_started_summary(data, context),
            data=safe_activity_data(payload),
            refs=self.activity_refs(data=data, output=None, context=context),
        )

    def build_activity_completed_event(
        self,
        *,
        tool_call: Any,
        data: InputT,
        output: OutputT,
        context: ToolExecutionContext,
    ) -> AgentActivityEvent:
        spec = self.activity_spec()
        payload = {
            "tool_call_id": getattr(tool_call, "id", None),
            "tool_name": self.name,
            **self.activity_completed_data(data, output, context),
        }
        return AgentActivityEvent(
            id=f"activity_{getattr(tool_call, 'id', self.name)}_completed",
            type=spec.completed_type,
            source=self._activity_source(),
            category=self.activity_category(data=data, output=output, error=None),
            status="success" if getattr(output, "ok", True) else "error",
            title=f"{spec.display_name} completed",
            summary=self.activity_completed_summary(data, output, context),
            data=safe_activity_data(payload),
            refs=self.activity_refs(data=data, output=output, context=context),
        )

    def build_activity_failed_event(
        self,
        *,
        tool_call: Any,
        data: InputT | None,
        error: BaseException,
        context: ToolExecutionContext,
    ) -> AgentActivityEvent:
        spec = self.activity_spec()
        payload = {
            "tool_call_id": getattr(tool_call, "id", None),
            "tool_name": self.name,
            **self.activity_failed_data(data, error, context),
        }
        return AgentActivityEvent(
            id=f"activity_{getattr(tool_call, 'id', self.name)}_failed",
            type=spec.failed_type,
            source=self._activity_source(),
            category=self.activity_category(data=data, output=None, error=error),
            status="error",
            title=f"{spec.display_name} failed",
            summary=self.activity_failed_summary(data, error, context),
            data=safe_activity_data(payload),
            refs=self.activity_refs(data=data, output=None, context=context),
        )

    def build_activity_blocked_event(
        self,
        *,
        tool_call: Any,
        data: InputT | None,
        reason: str,
        context: ToolExecutionContext,
    ) -> AgentActivityEvent:
        spec = self.activity_spec()
        event_type = spec.blocked_type or f"tool.{normalize_activity_namespace(self.name)}.blocked"
        payload = {
            "tool_call_id": getattr(tool_call, "id", None),
            "tool_name": self.name,
            "reason": reason,
            **self.activity_blocked_data(data, reason, context),
        }
        return AgentActivityEvent(
            id=f"activity_{getattr(tool_call, 'id', self.name)}_blocked",
            type=event_type,
            source=self._activity_source(),
            category=self.activity_category(data=data, output=None, error=None),
            status="blocked",
            title=f"{spec.display_name} blocked",
            summary=activity_text_summary(reason),
            data=safe_activity_data(payload),
            refs=self.activity_refs(data=data, output=None, context=context),
        )

    def activity_category(
        self,
        *,
        data: InputT | None,
        output: OutputT | None,
        error: BaseException | None,
    ) -> str:
        return self.activity_spec().category

    def activity_started_data(self, data: InputT | None, context: ToolExecutionContext) -> dict[str, Any]:
        return {"args": _model_activity_payload(data)}

    def activity_completed_data(self, data: InputT, output: OutputT, context: ToolExecutionContext) -> dict[str, Any]:
        content = getattr(output, "content", "")
        return {
            "ok": bool(getattr(output, "ok", True)),
            "content_chars": len(str(content)),
            "metadata": getattr(output, "metadata", {}) or {},
        }

    def activity_failed_data(
        self,
        data: InputT | None,
        error: BaseException,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        return {
            "error_type": error.__class__.__name__,
            "message": str(error),
            "args": _model_activity_payload(data),
        }

    def activity_blocked_data(self, data: InputT | None, reason: str, context: ToolExecutionContext) -> dict[str, Any]:
        return {"args": _model_activity_payload(data)}

    def activity_started_summary(self, data: InputT | None, context: ToolExecutionContext) -> str | None:
        return None

    def activity_completed_summary(self, data: InputT, output: OutputT, context: ToolExecutionContext) -> str | None:
        status = "ok" if getattr(output, "ok", True) else "error"
        return f"{self.name} finished with status {status}."

    def activity_failed_summary(self, data: InputT | None, error: BaseException, context: ToolExecutionContext) -> str | None:
        return activity_text_summary(error)

    def activity_refs(
        self,
        *,
        data: InputT | None,
        output: OutputT | None,
        context: ToolExecutionContext,
    ) -> list[AgentActivityRef]:
        return []

    def _activity_source(self) -> AgentActivitySource:
        return AgentActivitySource(kind="tool", name=self.name, component=self.__class__.__name__)

    def state_effects(
        self,
        *,
        tool_call: Any,
        result: Any,
        output: OutputT,
        state: dict[str, Any],
    ) -> list[ToolStateEffect]:
        output_data = output.model_dump(mode="json") if hasattr(output, "model_dump") else {}
        return [ToolStateEffect(kind=kind, data=output_data) for kind in self.runtime.state_effects]

    def metadata(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "safety": str(self.safety),
            "is_read_only": self.is_read_only,
            "requires_permission": self.requires_permission,
            "permission": self.permission.model_dump(mode="json"),
            "runtime": self.runtime.model_dump(mode="json"),
            "activity": self.activity_spec().model_dump(mode="json"),
            "input_schema": self.input_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
        }


def _model_activity_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json")
        return payload if isinstance(payload, dict) else {}
    if isinstance(value, dict):
        return dict(value)
    return {"value": value}
