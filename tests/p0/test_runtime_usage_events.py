"""Tests for live usage runtime event contracts."""

from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.api.schemas import ChatResponse
from langgraph_agent_blueprint.models import event

from .helpers import ai_final


def test_usage_updated_event_is_validated_and_serialized() -> None:
    item = event("usage_updated", usage={"context_used": 42, "context_max": 100, "context_percent": 42})

    assert item["type"] == "usage_updated"
    assert item["data"]["usage"] == {"context_used": 42, "context_max": 100, "context_percent": 42}


def test_model_call_usage_event_reports_current_context_fields(
    runtime_factory: Any,
    scripted_chat_model: Any,
    approving_permissions: Any,
    temp_project: Path,
) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=scripted_chat_model(steps=[ai_final("done")]),
        permissions=approving_permissions,
        config_overrides={"context_max_tokens": 1000},
    )

    result = runtime.invoke("hello")

    usage_events = [item for item in result["ui_events"] if item["type"] == "usage_updated"]
    assert usage_events
    usage = usage_events[-1]["data"]["usage"]
    assert usage["context_used"] > 0
    assert usage["context_max"] == 1000
    assert usage["context_percent"] == round(min(100, (usage["context_used"] / 1000) * 100), 2)
    assert result["usage"]["context_used"] == usage["context_used"]
    assert result["usage"]["context_max"] == 1000


def test_chat_response_serializes_usage() -> None:
    response = ChatResponse(session_id="session", thread_id="thread", events=[], usage={"context_used": 42})

    assert response.model_dump(mode="json")["usage"] == {"context_used": 42}
