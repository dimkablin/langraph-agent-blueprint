"""Tests for live usage runtime event contracts."""

from langgraph_agent_blueprint.models import event


def test_usage_updated_event_is_validated_and_serialized() -> None:
    item = event("usage_updated", usage={"context_used": 42, "context_max": 100, "context_percent": 42})

    assert item["type"] == "usage_updated"
    assert item["data"]["usage"] == {"context_used": 42, "context_max": 100, "context_percent": 42}
