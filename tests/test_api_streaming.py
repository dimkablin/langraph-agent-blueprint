"""Contract tests for live frontend event streaming over FastAPI."""

from __future__ import annotations

import json
from collections.abc import Iterable

from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def _sse_frames(text: str) -> list[dict]:
    frames: list[dict] = []
    for block in text.split("\n\n"):
        data_lines = [line.removeprefix("data:").strip() for line in block.splitlines() if line.startswith("data:")]
        if data_lines:
            frames.append(json.loads("\n".join(data_lines)))
    return frames


def _stream_frames(client: TestClient, payload: dict) -> tuple[str, list[dict]]:
    with client.stream("POST", "/chat/stream", json=payload) as response:
        assert response.status_code == 200
        content_type = response.headers["content-type"]
        body = "".join(response.iter_text())
    return content_type, _sse_frames(body)


def _events(frames: Iterable[dict]) -> list[dict]:
    return [frame["event"] for frame in frames if frame.get("type") == "event" and frame.get("event")]


def _event_types(frames: Iterable[dict]) -> list[str]:
    return [event["type"] for event in _events(frames)]


def test_chat_stream_endpoint_returns_sse_runtime_event_frames(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    content_type, frames = _stream_frames(client, {"message": "hello"})

    assert content_type.startswith("text/event-stream")
    assert frames
    assert frames[-1]["type"] == "done"
    assert "final_response" in _event_types(frames)
    for frame in frames[:-1]:
        assert frame["type"] == "event"
        assert {"id", "type", "timestamp", "session_id", "severity", "data"} <= set(frame["event"])


def test_chat_stream_preserves_runtime_event_envelope_for_long_model_output(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)
    message = "x" * 5000

    _content_type, frames = _stream_frames(client, {"message": message})

    assert not [frame for frame in frames if frame.get("type") == "error"]
    assert frames[-1]["type"] == "done"
    assert frames[-1]["final_response"] == f"Fake response: {message}"
    model_message = next(frame["event"] for frame in frames if frame.get("event", {}).get("type") == "model_message")
    assert {"id", "type", "timestamp", "session_id", "severity", "data"} <= set(model_message)
    assert model_message["data"]["content"] == f"Fake response: {message}"


def test_chat_stream_emits_model_tokens_before_completed_model_message(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    _content_type, frames = _stream_frames(client, {"message": "hello world"})
    events = _events(frames)
    event_types = [event["type"] for event in events]

    assert event_types.index("model_token") < event_types.index("model_message")
    assert "".join(event["data"]["token"] for event in events if event["type"] == "model_token") == "Fake response: hello world"


def test_chat_stream_auto_compacts_before_streaming_model_tokens(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake", auto_compact_threshold=2))
    client = TestClient(app)

    _content_type, frames = _stream_frames(client, {"message": "x" * 80})
    event_types = _event_types(frames)

    assert "compact_started" in event_types
    assert "compact_finished" in event_types
    assert "model_token" in event_types
    assert event_types.index("compact_started") < event_types.index("model_token")
    assert event_types.index("compact_finished") < event_types.index("model_token")


def test_chat_stream_context_fragment_event_includes_preview_for_frontend_window(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "README.md").write_text("FRONTEND_CONTEXT_WINDOW_TOKEN", encoding="utf-8")
    app = create_app(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=project_root,
            cwd=project_root,
            llm_provider="fake",
        )
    )
    client = TestClient(app)

    _content_type, frames = _stream_frames(client, {"message": "Use @README.md"})
    fragment_event = next(event for event in _events(frames) if event["type"] == "context_fragment_added")

    assert fragment_event["data"]["title"] == "README.md"
    assert fragment_event["data"]["preview"] == "FRONTEND_CONTEXT_WINDOW_TOKEN"


def test_chat_stream_emits_tool_execution_sequence_without_replaying_tokens(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "note.txt").write_text("tool-stream-ok", encoding="utf-8")
    app = create_app(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=project_root,
            cwd=project_root,
            llm_provider="fake",
        )
    )
    client = TestClient(app)

    _content_type, frames = _stream_frames(client, {"message": 'tool:read_file {"path":"note.txt"}'})
    events = _events(frames)
    event_types = [event["type"] for event in events]
    model_messages = [event["data"]["content"] for event in events if event["type"] == "model_message"]
    token_text = "".join(event["data"]["token"] for event in events if event["type"] == "model_token")

    assert not [frame for frame in frames if frame.get("type") == "error"]
    assert event_types.index("model_token") < event_types.index("model_message")
    assert event_types.index("tool_call_started") < event_types.index("tool_call_finished")
    assert event_types.index("tool_call_finished") < event_types.index("final_response")
    assert model_messages == ["Calling tool read_file", "Tool read_file ok: tool-stream-ok"]
    assert token_text == "Calling tool read_fileTool read_file ok: tool-stream-ok"
    assert frames[-1]["type"] == "done"
    assert frames[-1]["final_response"] == "Tool read_file ok: tool-stream-ok"


def test_chat_stream_does_not_replay_previous_turn_events(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    _first_content_type, first_frames = _stream_frames(client, {"message": "first", "thread_id": "stream-replay"})
    session_id = first_frames[-1]["session_id"]

    _second_content_type, second_frames = _stream_frames(
        client,
        {"message": "second", "session_id": session_id, "thread_id": "stream-replay"},
    )

    replayed = [
        frame
        for frame in second_frames
        if frame.get("type") == "event"
        and frame.get("event", {}).get("type") in {"model_message", "final_response"}
        and frame["event"].get("data", {}).get("content") == "Fake response: first"
    ]
    assert replayed == []
    assert second_frames[-1]["final_response"] == "Fake response: second"


def test_chat_stream_emits_permission_required_before_done(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    _content_type, frames = _stream_frames(
        client,
        {"message": "tool:write_file frontend-created.txt hello", "thread_id": "stream-permission"},
    )
    events = _events(frames)
    event_types = [event["type"] for event in events]

    permission_frames = [
        frame
        for frame in frames
        if frame.get("type") == "event" and frame.get("event", {}).get("type") == "permission_required"
    ]
    assert permission_frames
    permission_data = permission_frames[0]["event"]["data"]
    assert event_types.index("model_message") < event_types.index("permission_required")
    assert "tool_call_started" not in event_types
    assert "tool_call_finished" not in event_types
    assert permission_data["tool_name"] == "write_file"
    assert permission_data["args"] == {"path": "frontend-created.txt", "content": "hello"}
    assert permission_data["action"] == "write"
    assert permission_data["risk"] == "medium"
    assert frames[-1]["type"] == "done"
    assert frames[-1]["session_id"]
    assert frames[-1]["final_response"] is None


def test_chat_stream_emits_compaction_events_without_final_message(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    _content_type, frames = _stream_frames(client, {"message": "/compact", "thread_id": "stream-compact"})
    event_types = _event_types(frames)

    assert "compact_started" in event_types
    assert "compact_finished" in event_types
    assert event_types.index("compact_started") < event_types.index("compact_finished")
    assert "final_response" not in event_types
    assert frames[-1]["type"] == "done"
    assert frames[-1]["final_response"] is None


def test_chat_stream_invalid_request_uses_structured_validation_error(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    response = client.post("/chat/stream", json={"message": "hello", "session_id": "../evil"})

    assert response.status_code == 422
    assert response.json()["detail"]
