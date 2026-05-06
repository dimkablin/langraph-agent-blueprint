"""RuntimeEvent to Langfuse mapping tests."""

from __future__ import annotations

from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.observability import LangfuseConfig, TraceContext
from langgraph_agent_blueprint.services.observability_service import ObservabilityService

from tests.test_observability_service import RecordingLangfuseFactory


def _service(capture_inputs: bool = True, capture_outputs: bool = True) -> ObservabilityService:
    return ObservabilityService(
        LangfuseConfig(
            enabled=True,
            public_key="pk",
            secret_key="sk",
            base_url="https://langfuse.example",
            capture_inputs=capture_inputs,
            capture_outputs=capture_outputs,
        ),
        factory=RecordingLangfuseFactory(),
    )


def test_runtime_events_are_recorded_as_langfuse_events() -> None:
    service = _service()
    context = TraceContext(session_id="session-1", thread_id="thread-1")
    events = [
        event("tool_call_started", name="read_file", args={"path": "README.md"}),
        event("skill_started", name="remember"),
        event("permission_required", tool_name="write_file", action="write"),
        event("mcp_tool_call_finished", name="mcp.fake.echo", status="ok"),
        event("hook_error", hook_id="plugin.bad", error="broken", severity="error"),
        event("final_response", content="done"),
    ]

    with service.trace_turn(context, input_data={"message": "hello"}) as turn:
        turn.record_runtime_events(events)

    names = [item["name"] for item in service.client_events]
    assert "runtime.tool_call_started" in names
    assert "runtime.skill_started" in names
    assert "runtime.permission_required" in names
    assert "runtime.mcp_tool_call_finished" in names
    assert "runtime.hook_error" in names
    assert "runtime.final_response" in names
    assert service._client.unscoped_events == []  # type: ignore[union-attr]


def test_runtime_events_not_recorded_unscoped() -> None:
    service = _service()
    context = TraceContext(session_id="session-1", thread_id="thread-1")

    service.record_runtime_event(event("final_response", content="done"), context)

    assert service.client_events == []
    assert service._client is None


def test_runtime_event_mapping_redacts_secrets_and_truncates_large_payloads() -> None:
    service = _service()
    context = TraceContext(session_id="session-1")
    secret_event = event(
        "tool_call_started",
        name="bash",
        args={
            "command": "echo hello",
            "OPENAI_API_KEY": "sk-secret",
            "authorization": "Bearer token",
            "content": "x" * 20000,
        },
    )

    with service.trace_turn(context, input_data={"message": "hello"}) as turn:
        turn.record_runtime_event(secret_event)

    payload = service.client_events[0]["input"]
    assert "sk-secret" not in str(payload)
    assert "Bearer token" not in str(payload)
    assert "***" in str(payload)
    assert len(str(payload)) < 6000


def test_input_output_capture_flags_are_respected() -> None:
    service = _service(capture_inputs=False, capture_outputs=False)
    context = TraceContext(session_id="session-1")

    with service.trace_turn(context, input_data={"message": "private prompt"}) as turn:
        turn.record_runtime_events(
            [
                event("tool_call_started", name="read_file", args={"path": "secret.md"}),
                event("final_response", content="private response"),
            ]
        )

    assert "secret.md" not in str(service.client_events)
    assert "private response" not in str(service.client_events)
    assert "<redacted>" in str(service.client_events)
