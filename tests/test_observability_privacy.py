"""Privacy coverage for Langfuse trace payload sanitization."""

from __future__ import annotations

from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.observability import LangfuseConfig, TraceContext
from langgraph_agent_blueprint.services.observability_service import ObservabilityService

from tests.test_observability_service import RecordingLangfuseFactory


WINDOWS_ROOT = r"C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint"


def _service(*, include_paths: bool) -> tuple[ObservabilityService, RecordingLangfuseFactory]:
    factory = RecordingLangfuseFactory()
    service = ObservabilityService(
        LangfuseConfig(
            enabled=True,
            public_key="pk",
            secret_key="sk",
            base_url="https://langfuse.example",
            include_project_paths=include_paths,
        ),
        factory=factory,
    )
    return service, factory


def test_project_root_not_sent_as_full_path_by_default() -> None:
    service, factory = _service(include_paths=False)
    context = TraceContext(session_id="session-1", thread_id="thread-1", project_root=WINDOWS_ROOT)

    with service.trace_turn(context, input_data={"project_root": WINDOWS_ROOT}) as turn:
        turn.record_runtime_events(
            [
                event("session_started", project_root=WINDOWS_ROOT, cwd=WINDOWS_ROOT),
                event("final_response", content="done", cwd=WINDOWS_ROOT),
            ]
        )

    payload = str(factory.client.top_level_traces + factory.client.child_observations + factory.client.metadata_updates)
    assert WINDOWS_ROOT not in payload
    assert "langgraph-agent-blueprint" in payload
    assert "path_hash" in payload
    assert factory.client.unscoped_events == []


def test_project_root_full_path_allowed_when_enabled() -> None:
    service, factory = _service(include_paths=True)
    context = TraceContext(session_id="session-1", thread_id="thread-1", project_root=WINDOWS_ROOT)

    with service.trace_turn(context, input_data={"project_root": WINDOWS_ROOT}) as turn:
        turn.record_runtime_event(event("final_response", content="done", cwd=WINDOWS_ROOT))

    assert factory.client.top_level_traces[0]["input"]["project_root"] == WINDOWS_ROOT
