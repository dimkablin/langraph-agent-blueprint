"""Pydantic boundary tests for Langfuse observability models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.models.observability import LangfuseConfig, ObservabilityEvent, TraceContext, TraceMetadata


def test_langfuse_config_redacts_keys() -> None:
    config = LangfuseConfig(
        enabled=True,
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        base_url="https://langfuse.example",
        environment="dev",
    )

    redacted = config.redacted()

    assert redacted["public_key"] == "***"
    assert redacted["secret_key"] == "***"
    assert redacted["base_url"] == "https://langfuse.example"


def test_trace_context_and_metadata_are_json_serializable() -> None:
    context = TraceContext(
        session_id="session-1",
        thread_id="thread-1",
        project_root="langgraph-agent-blueprint",
        environment="dev",
        tags=["langgraph-agent-blueprint"],
        metadata={"project_root_hash": "abc123"},
    )
    metadata = TraceMetadata(
        provider="fake",
        model="fake-model",
        active_tool="read_file",
        plugin_names=["superpowers"],
        mcp_servers=["fake"],
    )

    assert context.model_dump(mode="json")["session_id"] == "session-1"
    assert metadata.model_dump(mode="json")["mcp_servers"] == ["fake"]


def test_observability_event_validates_severity() -> None:
    event = ObservabilityEvent(type="runtime", name="runtime.final_response", session_id="session-1", severity="info")

    assert event.name == "runtime.final_response"

    with pytest.raises(ValidationError):
        ObservabilityEvent(type="runtime", name="bad", session_id="session-1", severity="fatal")  # type: ignore[arg-type]
