"""Observability tests for context runtime events."""

from __future__ import annotations

from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.observability import LangfuseConfig, TraceContext
from langgraph_agent_blueprint.services.observability_service import ObservabilityService

from tests.test_observability_service import RecordingLangfuseFactory


WINDOWS_ROOT = r"C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint"


def test_context_events_are_scoped_and_do_not_leak_full_paths() -> None:
    factory = RecordingLangfuseFactory()
    service = ObservabilityService(
        LangfuseConfig(enabled=True, public_key="pk", secret_key="sk", base_url="https://langfuse.example"),
        factory=factory,
    )

    with service.trace_turn(TraceContext(session_id="session-1", thread_id="thread-1", project_root=WINDOWS_ROOT)) as turn:
        turn.record_runtime_events(
            [
                event("context_fragment_added", path=WINDOWS_ROOT, content="x" * 5000),
                event("context_resolution_error", path=WINDOWS_ROOT, message="blocked"),
            ]
        )

    payload = str(factory.client.child_observations + factory.client.metadata_updates)
    assert WINDOWS_ROOT not in payload
    assert "langgraph-agent-blueprint" in payload
    assert len(payload) < 4000
    assert factory.client.unscoped_events == []
