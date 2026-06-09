"""P0 streaming coverage for subagent ReAct visibility."""

from __future__ import annotations

from types import SimpleNamespace
from time import monotonic, sleep
from typing import Any

from langchain_core.messages import AIMessage

from langgraph_agent_blueprint.api.serializers import child_run_list_item_dto, session_detail_dto
from langgraph_agent_blueprint.models import ChildRunMetadata, ModelRequest, ModelResponse, ModelStreamEvent, Usage
from langgraph_agent_blueprint.services.permission_service import PermissionService


class StreamingTwoSubagentsModel:
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("Streaming runtime must not fall back to non-streaming generation.")

    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        text = _latest_human_text(request)
        tool_result_count = _tool_result_count(request)
        if tool_result_count >= 2:
            return _text_response("Both subagents finished.")
        if text == "Build backend":
            return _text_response("Backend subagent done.")
        if text == "Build frontend":
            return _text_response("Frontend subagent done.")
        tool_calls = [
            {
                "id": "backend_agent",
                "name": "agent",
                "args": {"prompt": "Build backend", "name": "backend", "max_turns": 2},
            },
            {
                "id": "frontend_agent",
                "name": "agent",
                "args": {"prompt": "Build frontend", "name": "frontend", "max_turns": 2},
            },
        ]
        return [
            ModelStreamEvent(type="token", token="Now create two agents:"),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="Now create two agents:",
                    tool_calls=tool_calls,
                    raw=AIMessage(content="Now create two agents:", tool_calls=tool_calls),
                    usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            ),
        ]


class SlowConcurrentTwoSubagentsModel(StreamingTwoSubagentsModel):
    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        text = _latest_human_text(request)
        if text == "Build backend":
            sleep(0.2)
        return super().stream_generate(request)


class VerySlowConcurrentTwoSubagentsModel(StreamingTwoSubagentsModel):
    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        text = _latest_human_text(request)
        if text == "Build backend":
            sleep(0.6)
        return super().stream_generate(request)


class ContractThenTwoSubagentsModel:
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("Streaming runtime must not fall back to non-streaming generation.")

    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        text = _latest_human_text(request)
        tool_result_count = _tool_result_count(request)
        if text == "Build backend":
            return _text_response("Backend subagent done.")
        if text == "Build frontend":
            return _text_response("Frontend subagent done.")
        if tool_result_count >= 3:
            return _text_response("Contract and both subagents finished.")
        if tool_result_count >= 1:
            tool_calls = [
                {
                    "id": "backend_agent_after_contract",
                    "name": "agent",
                    "args": {"prompt": "Build backend", "name": "backend", "max_turns": 2},
                },
                {
                    "id": "frontend_agent_after_contract",
                    "name": "agent",
                    "args": {"prompt": "Build frontend", "name": "frontend", "max_turns": 2},
                },
            ]
            return [
                ModelStreamEvent(type="token", token="Contract updated. Now create two subagents."),
                ModelStreamEvent(
                    type="response",
                    response=ModelResponse(
                        content="Contract updated. Now create two subagents.",
                        tool_calls=tool_calls,
                        raw=AIMessage(content="Contract updated. Now create two subagents.", tool_calls=tool_calls),
                        usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
                    ),
                ),
            ]
        tool_call = {
            "id": "contract_write",
            "name": "write_file",
            "args": {"path": "common/CONTRACT.md", "content": "# Contract\n\nUse POST /api/calculate.\n"},
        }
        return [
            ModelStreamEvent(type="token", token="First update the frontend/backend contract."),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="First update the frontend/backend contract.",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="First update the frontend/backend contract.", tool_calls=[tool_call]),
                    usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            ),
        ]


class ChildWriteAttemptModel:
    def __init__(self, *, request_allowed_write: bool = False) -> None:
        self.request_allowed_write = request_allowed_write

    def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("Streaming runtime must not fall back to non-streaming generation.")

    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        text = _latest_human_text(request)
        if _tool_result_count(request) >= 1 and text == "Write child file":
            return _text_response("Child write attempt resolved.")
        if _tool_result_count(request) >= 1:
            return _text_response("Parent observed child result.")
        if text == "Write child file":
            tool_call = {
                "id": "child_write",
                "name": "write_file",
                "args": {"path": "child.txt", "content": "child wrote this\n"},
            }
            return [
                ModelStreamEvent(type="token", token="Child will try to write."),
                ModelStreamEvent(
                    type="response",
                    response=ModelResponse(
                        content="Child will try to write.",
                        tool_calls=[tool_call],
                        raw=AIMessage(content="Child will try to write.", tool_calls=[tool_call]),
                        usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
                    ),
                ),
            ]
        args = {"prompt": "Write child file", "name": "writer", "max_turns": 3}
        if self.request_allowed_write:
            args["allowed_tools"] = ["write_file"]
        tool_call = {"id": "writer_agent", "name": "agent", "args": args}
        return [
            ModelStreamEvent(type="token", token="Parent starts writer subagent."),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="Parent starts writer subagent.",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="Parent starts writer subagent.", tool_calls=[tool_call]),
                    usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            ),
        ]


def test_stream_forwards_each_subagent_run_and_child_tokens(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingTwoSubagentsModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Create backend and frontend subagents.",
            project_root=temp_project,
            thread_id="thread_subagent_stream_123",
            session_id="session_subagent_stream_123",
        )
    )

    event_types = [item["type"] for item in events]
    started = [item for item in events if item["type"] == "subagent_started"]
    finished = [item for item in events if item["type"] == "subagent_finished"]
    child_token_events = [
        item
        for item in events
        if item["type"] == "subagent_event" and item.get("data", {}).get("child_event_type") == "model_token"
    ]

    assert event_types.index("model_token") < event_types.index("subagent_started")
    assert [item["data"]["name"] for item in started] == ["backend", "frontend"]
    assert sorted(item["data"]["name"] for item in finished) == ["backend", "frontend"]
    assert len(child_token_events) >= 2
    assert event_types.count("subagent_started") == 2
    assert event_types.count("subagent_finished") == 2
    assert any(item["type"] == "final_response" and item["data"].get("content") == "Both subagents finished." for item in events)
    _assert_typed_subagent_streams_are_ordered(events)


def test_stream_starts_multiple_subagents_before_first_child_finishes(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=SlowConcurrentTwoSubagentsModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Create backend and frontend subagents.",
            project_root=temp_project,
            thread_id="thread_subagent_parallel_123",
            session_id="session_subagent_parallel_123",
        )
    )

    first_finish_index = next(index for index, item in enumerate(events) if item["type"] == "subagent_finished")
    started_before_first_finish = [
        item["data"]["name"]
        for item in events[:first_finish_index]
        if item["type"] == "subagent_started"
    ]

    assert started_before_first_finish == ["backend", "frontend"]


def test_stream_yields_subagent_started_before_slow_child_finishes(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=VerySlowConcurrentTwoSubagentsModel(),
        permissions=approving_permissions,
    )
    stream = runtime.stream(
        "Create backend and frontend subagents.",
        project_root=temp_project,
        thread_id="thread_subagent_live_start_123",
        session_id="session_subagent_live_start_123",
    )
    started_at = monotonic()
    first_started_elapsed: float | None = None
    try:
        for item in stream:
            if item["type"] == "subagent_started":
                first_started_elapsed = monotonic() - started_at
                break
    finally:
        close = getattr(stream, "close", None)
        if close is not None:
            close()

    assert first_started_elapsed is not None
    assert first_started_elapsed < 0.4


def test_stream_emits_parallel_subagent_start_batch_before_child_events(
    runtime_factory,
    approving_permissions,
    temp_project,
    monkeypatch,
) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingTwoSubagentsModel(),
        permissions=approving_permissions,
    )
    original_create_child_state = runtime.dependencies.agent_service.create_child_state

    def delayed_create_child_state(parent_state, request, metadata, tool_registry):
        if request.name == "frontend":
            sleep(0.15)
        return original_create_child_state(parent_state, request, metadata, tool_registry)

    monkeypatch.setattr(runtime.dependencies.agent_service, "create_child_state", delayed_create_child_state)
    stream = runtime.stream(
        "Create backend and frontend subagents.",
        project_root=temp_project,
        thread_id="thread_subagent_start_batch_123",
        session_id="session_subagent_start_batch_123",
    )
    events: list[dict[str, Any]] = []
    try:
        for item in stream:
            events.append(item)
            if item["type"] == "subagent_event":
                break
    finally:
        close = getattr(stream, "close", None)
        if close is not None:
            close()

    first_child_event_index = next(index for index, item in enumerate(events) if item["type"] == "subagent_event")
    started_before_child_events = [
        item["data"]["name"]
        for item in events[:first_child_event_index]
        if item["type"] == "subagent_started"
    ]

    assert started_before_child_events == ["backend", "frontend"]


def test_stream_runs_contract_tool_before_launching_two_subagents(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=ContractThenTwoSubagentsModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Create two subagents for React frontend and FastAPI backend, but fix the contract first.",
            project_root=temp_project,
            thread_id="thread_contract_then_subagents_123",
            session_id="session_contract_then_subagents_123",
        )
    )

    event_types = [item["type"] for item in events]
    write_finished_index = next(
        index
        for index, item in enumerate(events)
        if item["type"] == "tool_call_finished" and item.get("data", {}).get("name") == "write_file"
    )
    first_subagent_index = event_types.index("subagent_started")
    started = [item for item in events if item["type"] == "subagent_started"]
    finished = [item for item in events if item["type"] == "subagent_finished"]
    parent_session = runtime.dependencies.session_storage.load_session(temp_project, "session_contract_then_subagents_123")

    assert write_finished_index < first_subagent_index
    assert [item["data"]["name"] for item in started] == ["backend", "frontend"]
    assert sorted(item["data"]["name"] for item in finished) == ["backend", "frontend"]
    assert event_types.count("subagent_started") == 2
    assert event_types.count("subagent_finished") == 2
    assert [item["name"] for item in parent_session["tool_calls"]] == ["write_file", "agent", "agent"]
    assert (temp_project / "common" / "CONTRACT.md").read_text(encoding="utf-8").startswith("# Contract")
    assert any(
        item["type"] == "final_response" and item["data"].get("content") == "Contract and both subagents finished."
        for item in events
    )


def test_subagent_default_tool_scope_blocks_child_write_tool(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=ChildWriteAttemptModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Ask a child to write.",
            project_root=temp_project,
            thread_id="thread_subagent_scope_123",
            session_id="session_subagent_scope_123",
        )
    )

    child_event_types = [
        item["data"].get("child_event", {}).get("type")
        for item in events
        if item["type"] == "subagent_event"
    ]

    assert "tool_call_error" in child_event_types
    assert not (temp_project / "child.txt").exists()


def test_subagent_side_effect_approval_interrupts_parent_and_resumes_child(runtime_factory, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=ChildWriteAttemptModel(request_allowed_write=True),
        permissions=PermissionService("default"),
    )

    events = list(
        runtime.stream(
            "Ask a child to write with write_file allowed.",
            project_root=temp_project,
            thread_id="thread_subagent_nested_approval_123",
            session_id="session_subagent_nested_approval_123",
        )
    )

    permission_events = [item for item in events if item["type"] == "permission_required"]

    assert permission_events
    permission = permission_events[-1]["data"]
    assert permission["scope"] == "subagent"
    assert permission["child_thread_id"]
    assert permission["child_session_id"]
    assert not (temp_project / "child.txt").exists()

    result = runtime.resume(
        "thread_subagent_nested_approval_123",
        {
            "tool_call_id": permission["tool_call_id"],
            "decision": "approved",
            "reason": "approved by test user",
        },
        session_id="session_subagent_nested_approval_123",
    )

    assert "__interrupt__" not in result
    assert result["final_response"] == "Parent observed child result."
    assert (temp_project / "child.txt").read_text(encoding="utf-8") == "child wrote this\n"
    assert any(item["type"] == "permission_resolved" and item["data"].get("approved") is True for item in result["ui_events"])
    assert any(item["type"] == "subagent_finished" for item in result["ui_events"])


def test_subagent_child_resume_repairs_required_state_channels(monkeypatch, tmp_path) -> None:
    from langgraph_agent_blueprint.graph import builder as builder_module
    from langgraph_agent_blueprint.graph.subgraphs.agent_graph import _resume_child_graph

    captured: dict[str, Any] = {}

    class FakeCompiledGraph:
        def invoke(self, command, config):
            captured["command"] = command
            captured["config"] = config
            return {"final_response": "child resumed", "ui_events": []}

    class FakeGraphBuilder:
        def compile(self, checkpointer=None):
            captured["checkpointer"] = checkpointer
            return FakeCompiledGraph()

    monkeypatch.setattr(builder_module, "build_main_graph", lambda deps: FakeGraphBuilder())

    metadata = ChildRunMetadata(
        child_run_id="child_resume_123",
        parent_session_id="session_parent_123",
        parent_thread_id="thread_parent_123",
        child_session_id="session_child_123",
        child_thread_id="thread_child_123",
        name="writer",
        status="running",
        started_at="2026-06-09T00:00:00Z",
        metadata={"agent_call_id": "writer_agent"},
    )
    pending = {
        "request": {"prompt": "Write child file", "name": "writer", "max_turns": 3},
        "child_state": {
            "session_id": metadata.child_session_id,
            "thread_id": metadata.child_thread_id,
            "project_root": str(tmp_path),
            "project_id": "project_123",
            "workspace": {"root_path": str(tmp_path)},
            "cwd": str(tmp_path),
            "input_text": "Write child file",
            "input_kind": "headless",
            "metadata": {"is_subagent": True, "subagent_depth": 1},
        },
        "child_events": [],
    }
    deps = SimpleNamespace(
        config=SimpleNamespace(storage_dir=tmp_path),
        agent_service=SimpleNamespace(child_checkpointer=lambda storage_dir: "child-checkpointer"),
    )

    _resume_child_graph(
        deps,
        pending,
        {"tool_call_id": "child_write", "decision": "approved"},
        {"session_id": metadata.parent_session_id},
        metadata,
        None,
    )

    command = captured["command"]
    assert command.resume == {"tool_call_id": "child_write", "decision": "approved"}
    assert command.update["session_id"] == metadata.child_session_id
    assert command.update["thread_id"] == metadata.child_thread_id
    assert command.update["project_root"] == str(tmp_path)
    assert command.update["cwd"] == str(tmp_path)
    assert command.update["metadata"]["child_session_id"] == metadata.child_session_id
    assert command.update["metadata"]["child_thread_id"] == metadata.child_thread_id
    assert captured["config"]["configurable"]["thread_id"] == metadata.child_thread_id


def test_subagent_side_effect_rejection_finishes_child_without_execution(runtime_factory, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=ChildWriteAttemptModel(request_allowed_write=True),
        permissions=PermissionService("default"),
    )

    events = list(
        runtime.stream(
            "Ask a child to write with write_file allowed.",
            project_root=temp_project,
            thread_id="thread_subagent_rejected_approval_123",
            session_id="session_subagent_rejected_approval_123",
        )
    )
    permission = [item for item in events if item["type"] == "permission_required"][-1]["data"]

    result = runtime.resume(
        "thread_subagent_rejected_approval_123",
        {
            "tool_call_id": permission["tool_call_id"],
            "decision": "rejected",
            "reason": "rejected by test user",
        },
        session_id="session_subagent_rejected_approval_123",
    )

    assert "__interrupt__" not in result
    assert result["final_response"] == "Parent observed child result."
    assert not (temp_project / "child.txt").exists()
    assert any(item["type"] == "permission_resolved" and item["data"].get("approved") is False for item in result["ui_events"])
    subagent_errors = [item for item in result["ui_events"] if item["type"] == "subagent_error"]
    assert subagent_errors
    error_stream = subagent_errors[-1]["data"].get("stream_event", {})
    assert error_stream.get("kind") == "subagent"
    assert error_stream.get("phase") == "error"
    assert error_stream.get("run_id") == subagent_errors[-1]["data"].get("child_run_id")
    assert error_stream.get("error", {}).get("type") == "SubagentPermissionRejected"


def test_subagent_inherits_runtime_permission_mode_for_allowed_side_effects(runtime_factory, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=ChildWriteAttemptModel(request_allowed_write=True),
        permissions=PermissionService("default"),
    )

    events = list(
        runtime.stream(
            "Ask a child to write with full access.",
            project_root=temp_project,
            thread_id="thread_subagent_full_access_123",
            session_id="session_subagent_full_access_123",
            permission_mode="bypass_read_only",
        )
    )

    errors = [item for item in events if item["type"] == "subagent_error"]
    finished = [item for item in events if item["type"] == "subagent_finished"]

    assert errors == []
    assert finished
    assert (temp_project / "child.txt").read_text(encoding="utf-8") == "child wrote this\n"


def test_stream_persists_each_child_run_with_streamed_child_events(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingTwoSubagentsModel(),
        permissions=approving_permissions,
    )

    list(
        runtime.stream(
            "Create backend and frontend subagents.",
            project_root=temp_project,
            thread_id="thread_subagent_storage_123",
            session_id="session_subagent_storage_123",
        )
    )

    child_runs = runtime.dependencies.session_storage.list_child_runs(temp_project, "session_subagent_storage_123")
    parent_session = runtime.dependencies.session_storage.load_session(temp_project, "session_subagent_storage_123")

    assert [item["metadata"]["name"] for item in child_runs] == ["backend", "frontend"]
    assert [item["name"] for item in parent_session["tool_calls"]] == ["agent", "agent"]
    detail = session_detail_dto(
        parent_session,
        child_runs=[child_run_list_item_dto(item["metadata"], item.get("result", {})) for item in child_runs],
    )
    assert [item.name for item in detail.tool_calls] == ["agent", "agent"]
    assert [item.name for item in detail.child_runs] == ["backend", "frontend"]
    for child_run in child_runs:
        detail = runtime.dependencies.session_storage.load_child_run(
            temp_project,
            "session_subagent_storage_123",
            child_run["metadata"]["child_run_id"],
        )
        event_types = [item["type"] for item in detail["events"]]
        assert "user_message" in event_types
        assert "model_token" in event_types
        assert "final_response" in event_types


def test_stream_emits_user_message_event_for_session_replay(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingTwoSubagentsModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Create backend and frontend subagents.",
            project_root=temp_project,
            thread_id="thread_user_event_123",
            session_id="session_user_event_123",
        )
    )

    user_events = [item for item in events if item["type"] == "user_message"]

    assert len(user_events) == 1
    assert user_events[0]["data"]["content"] == "Create backend and frontend subagents."


def _text_response(content: str) -> list[ModelStreamEvent]:
    return [
        ModelStreamEvent(type="token", token=content),
        ModelStreamEvent(
            type="response",
            response=ModelResponse(
                content=content,
                raw=AIMessage(content=content),
                usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            ),
        ),
    ]


def _latest_human_text(request: ModelRequest) -> str:
    for message in reversed(request.messages):
        if getattr(message, "type", "") == "human":
            return str(getattr(message, "content", ""))
    return ""


def _tool_result_count(request: ModelRequest) -> int:
    return sum(1 for message in request.messages if getattr(message, "type", "") == "tool")


def _assert_typed_subagent_streams_are_ordered(events: list[dict[str, Any]]) -> None:
    subagent_events = [
        item
        for item in events
        if item["type"] in {"subagent_started", "subagent_event", "subagent_finished", "subagent_error", "subagent_cancelled", "subagent_timeout"}
    ]
    by_run: dict[str, list[dict[str, Any]]] = {}
    for item in subagent_events:
        stream_event = item.get("data", {}).get("stream_event", {})
        assert stream_event.get("kind") == "subagent"
        assert stream_event.get("run_id") == item.get("data", {}).get("child_run_id")
        assert stream_event.get("subagent_id")
        assert isinstance(stream_event.get("sequence"), int)
        by_run.setdefault(stream_event["run_id"], []).append(stream_event)

    assert len(by_run) == 2
    for run_id, items in by_run.items():
        sequences = [item["sequence"] for item in items]
        assert sequences == sorted(sequences), run_id
        assert sequences == list(dict.fromkeys(sequences)), run_id
        assert sequences[0] == 0
        assert {item["phase"] for item in items} >= {"started", "finished"}
        assert len({item["subagent_id"] for item in items}) == 1
