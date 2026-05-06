"""Pydantic contracts for slash-command parsing and command execution results."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base import FrozenRuntimeModel


CommandType = Literal["local", "session", "skill", "prompt", "diagnostic", "unsupported"]
CommandRoute = Literal["finalize", "model", "skill", "compact", "resume", "export", "diagnostics"]


class ParsedCommand(FrozenRuntimeModel):
    """Validated slash-command parse result at the user-input boundary."""

    name: str
    args: str = ""
    raw: str
    command_type: CommandType


class CommandResult(FrozenRuntimeModel):
    """Validated command handler result that drives command graph routing."""

    handled: bool
    response: str | None = None
    prompt: str | None = None
    skill: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    route: CommandRoute = "finalize"
    final_response: str | None = None

    def __init__(
        self,
        handled: bool,
        response: str | None = None,
        *,
        prompt: str | None = None,
        skill: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        route: CommandRoute | None = None,
        final_response: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "handled": handled,
            "response": response,
            "prompt": prompt,
            "skill": skill,
            "metadata": metadata or {},
            "final_response": final_response,
        }
        if route is not None:
            payload["route"] = route
        super().__init__(**payload)

    @model_validator(mode="before")
    @classmethod
    def _derive_route_and_response(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if payload.get("final_response") is None and payload.get("response") is not None:
            payload["final_response"] = payload["response"]
        if payload.get("route"):
            return payload
        metadata = payload.get("metadata") or {}
        if payload.get("skill") is not None:
            payload["route"] = "skill"
        elif metadata.get("compact_requested"):
            payload["route"] = "compact"
        elif metadata.get("resume"):
            payload["route"] = "resume"
        elif metadata.get("export_requested"):
            payload["route"] = "export"
        elif metadata.get("doctor_requested"):
            payload["route"] = "diagnostics"
        elif payload.get("prompt") is not None:
            payload["route"] = "model"
        else:
            payload["route"] = "finalize"
        return payload
