"""Open, producer-owned activity event contracts for frontend timelines."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from langgraph_agent_blueprint.utils.ids import new_id

from .base import FrozenRuntimeModel


AgentActivityStatus = Literal["pending", "running", "success", "error", "blocked"]


class AgentActivitySource(FrozenRuntimeModel):
    """The runtime component, tool, skill, or permission layer that emitted activity."""

    kind: str
    name: str | None = None
    component: str | None = None


class AgentActivityRef(FrozenRuntimeModel):
    """Safe reference attached to an activity item."""

    kind: str
    path: str | None = None
    name: str | None = None
    id: str | None = None


class AgentActivityEvent(FrozenRuntimeModel):
    """Frontend-visible activity payload carried inside RuntimeEvent.data['activity'].

    The event type is intentionally an open namespaced string owned by the producer.
    """

    id: str = Field(default_factory=lambda: new_id("activity"))
    type: str
    source: AgentActivitySource
    category: str
    status: AgentActivityStatus | None = None
    title: str
    summary: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    refs: list[AgentActivityRef] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def type_must_be_namespaced(cls, value: str) -> str:
        text = value.strip()
        if not text or "." not in text:
            raise ValueError("activity type must be a non-empty namespaced string")
        return text

    @field_validator("category")
    @classmethod
    def category_must_be_non_empty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("activity category must be non-empty")
        return text
