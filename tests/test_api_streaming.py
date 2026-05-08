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


def _event_types(frames: Iterable[dict]) -> list[str]:
    return [frame["event"]["type"] for frame in frames if frame.get("type") == "event" and frame.get("event")]


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


def test_chat_stream_emits_permission_required_before_done(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    _content_type, frames = _stream_frames(
        client,
        {"message": "tool:write_file frontend-created.txt hello", "thread_id": "stream-permission"},
    )

    permission_frames = [
        frame
        for frame in frames
        if frame.get("type") == "event" and frame.get("event", {}).get("type") == "permission_required"
    ]
    assert permission_frames
    assert permission_frames[0]["event"]["data"]["tool_name"] == "write_file"
    assert frames[-1]["type"] == "done"


def test_chat_stream_invalid_request_uses_structured_validation_error(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    response = client.post("/chat/stream", json={"message": "hello", "session_id": "../evil"})

    assert response.status_code == 422
    assert response.json()["detail"]

