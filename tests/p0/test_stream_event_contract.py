"""P0 coverage for the public typed runtime stream contract."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from langgraph_agent_blueprint.models import ModelRequest, ModelResponse, ModelStreamEvent, Usage
from langgraph_agent_blueprint.services.permission_service import PermissionService


class StreamingContractModel:
    """Deterministic streaming model for public runtime.stream contract tests."""

    def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("Streaming contract tests must use stream_generate().")

    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        tool_result_count = _tool_result_count(request)
        if tool_result_count:
            return _text_response("Final answer after tool.")
        return _text_response("Hello world")


class StreamingToolCycleModel(StreamingContractModel):
    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        if _tool_result_count(request):
            return _text_response("Read complete.")
        tool_call = {"id": "read_contract", "name": "read_file", "args": {"path": "README.md"}}
        return [
            ModelStreamEvent(type="token", token="Reading project file."),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="Reading project file.",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="Reading project file.", tool_calls=[tool_call]),
                    usage=_usage("Reading project file."),
                ),
            ),
        ]


class StreamingFailedToolModel(StreamingContractModel):
    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        if _tool_result_count(request):
            return _text_response("Failure handled.")
        tool_call = {"id": "bad_read", "name": "read_file", "args": {}}
        return [
            ModelStreamEvent(type="token", token="Trying a read."),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="Trying a read.",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="Trying a read.", tool_calls=[tool_call]),
                    usage=_usage("Trying a read."),
                ),
            ),
        ]


class StreamingPermissionModel(StreamingContractModel):
    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        tool_call = {"id": "write_contract", "name": "write_file", "args": {"path": "README.md", "content": "updated"}}
        return [
            ModelStreamEvent(type="token", token="Need to write a file."),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="Need to write a file.",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="Need to write a file.", tool_calls=[tool_call]),
                    usage=_usage("Need to write a file."),
                ),
            ),
        ]


class StreamingUnknownToolModel(StreamingContractModel):
    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        tool_call = {"id": "missing_tool_call", "name": "missing_tool", "args": {}}
        return [
            ModelStreamEvent(type="token", token="Trying an unavailable tool."),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="Trying an unavailable tool.",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="Trying an unavailable tool.", tool_calls=[tool_call]),
                    usage=_usage("Trying an unavailable tool."),
                ),
            ),
        ]


def test_stream_contract_streams_assistant_deltas_and_finalizes_once(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingContractModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Say hello",
            project_root=temp_project,
            thread_id="thread_typed_assistant_123",
            session_id="session_typed_assistant_123",
        )
    )

    typed_events = _typed_events(events)
    deltas = [item for item in typed_events if item["kind"] == "assistant_delta"]
    finals = [item for item in typed_events if item["kind"] == "assistant_final"]

    assert [item["delta"] for item in deltas] == ["Hello world"]
    assert len(finals) == 1
    assert finals[0]["content"] == "Hello world"
    assert {item["message_id"] for item in [*deltas, *finals]} == {finals[0]["message_id"]}
    assert [item["type"] for item in events].count("final_response") == 1


def test_stream_contract_orders_react_tool_lifecycle_with_linked_result(runtime_factory, approving_permissions, temp_project) -> None:
    (temp_project / "README.md").write_text("contract", encoding="utf-8")
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingToolCycleModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Read README",
            project_root=temp_project,
            thread_id="thread_typed_react_123",
            session_id="session_typed_react_123",
        )
    )

    typed_events = _typed_events(events)
    lifecycle = [item for item in typed_events if item["kind"] == "tool_lifecycle"]
    phases = [item["phase"] for item in lifecycle if item["tool_call_id"] == "read_contract"]
    ordered_kinds = [item["kind"] for item in typed_events]

    assert ordered_kinds.index("assistant_delta") < ordered_kinds.index("tool_lifecycle")
    assert phases == ["started", "completed"]
    assert lifecycle[-1]["tool_name"] == "read_file"
    assert lifecycle[-1]["result_summary"]
    assert any(item["kind"] == "assistant_final" and item["content"] == "Read complete." for item in typed_events)


def test_stream_contract_emits_structured_tool_failure(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingFailedToolModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Read without args",
            project_root=temp_project,
            thread_id="thread_typed_failure_123",
            session_id="session_typed_failure_123",
        )
    )

    failures = [
        item
        for item in _typed_events(events)
        if item["kind"] == "tool_lifecycle" and item["phase"] == "failed"
    ]

    assert len(failures) == 1
    assert failures[0]["tool_call_id"] == "bad_read"
    assert failures[0]["tool_name"] == "read_file"
    assert failures[0]["error"]["type"]
    assert failures[0]["error"]["message"]


def test_stream_contract_emits_permission_required_as_explicit_state(runtime_factory, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingPermissionModel(),
        permissions=PermissionService("default"),
    )

    events = list(
        runtime.stream(
            "Write README",
            project_root=temp_project,
            thread_id="thread_typed_permission_123",
            session_id="session_typed_permission_123",
        )
    )

    permissions = [item for item in _typed_events(events) if item["kind"] == "permission_state"]

    assert len(permissions) == 1
    assert permissions[0]["status"] == "required"
    assert permissions[0]["tool_call_id"] == "write_contract"
    assert permissions[0]["tool_name"] == "write_file"
    assert permissions[0]["reason"] == "This tool modifies files."


def test_stream_contract_emits_runtime_errors_as_typed_payloads(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingUnknownToolModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Call missing tool",
            project_root=temp_project,
            thread_id="thread_typed_error_123",
            session_id="session_typed_error_123",
        )
    )

    errors = [item for item in _typed_events(events) if item["kind"] == "error"]

    assert len(errors) == 1
    assert errors[0]["error_type"] == "UnknownTool"
    assert "missing_tool" in errors[0]["message"]


def _typed_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads = []
    for event in events:
        data = event.get("data")
        stream_event = data.get("stream_event") if isinstance(data, dict) else None
        if isinstance(stream_event, dict):
            payloads.append(stream_event)
    assert payloads, f"Expected typed stream_event payloads in public runtime stream; saw event types {[event.get('type') for event in events]}"
    return payloads


def _text_response(content: str) -> list[ModelStreamEvent]:
    return [
        ModelStreamEvent(type="token", token=content),
        ModelStreamEvent(
            type="response",
            response=ModelResponse(
                content=content,
                raw=AIMessage(content=content),
                usage=_usage(content),
            ),
        ),
    ]


def _tool_result_count(request: ModelRequest) -> int:
    return sum(1 for message in request.messages if getattr(message, "type", "") == "tool")


def _usage(text: str) -> Usage:
    tokens = max(1, len(text) // 4)
    return Usage(input_tokens=tokens, output_tokens=tokens, total_tokens=tokens * 2)
