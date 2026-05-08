"""Typed skill side-effect envelopes and controlled applier."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field

from langgraph_agent_blueprint.models import FrozenRuntimeModel, event

if TYPE_CHECKING:
    from langgraph_agent_blueprint.dependencies import AppDependencies


class SkillEffect(FrozenRuntimeModel):
    """Controlled side effect requested by a skill invocation."""

    kind: Literal["write_memory"]
    data: dict[str, Any] = Field(default_factory=dict)


def apply_skill_effects(effects: list[SkillEffect], state: dict[str, Any], deps: "AppDependencies") -> dict[str, Any]:
    """Apply validated skill effects through runtime services."""

    update: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    for effect in effects:
        if effect.kind == "write_memory":
            scope = str(effect.data.get("scope") or "session")
            text = str(effect.data.get("text") or "").strip()
            if scope not in {"user", "project", "session"} or not text:
                continue
            path = deps.memory_service.remember(scope, text, state.get("session_id"))
            update["memory"] = deps.memory_service.load_memory(state.get("project_root"), state.get("session_id"))
            update["final_response"] = f"Remembered in {scope} memory: {text}"
            events.append(event("memory_updated", scope=scope, path=str(path)))
    if events:
        update["ui_events"] = events
    return update
