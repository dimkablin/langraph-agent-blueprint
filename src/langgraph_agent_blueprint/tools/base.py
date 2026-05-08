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

from langgraph_agent_blueprint.models import ToolPermissionMetadata, ToolRuntimeMetadata, ToolStateEffect


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
            "input_schema": self.input_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
        }

