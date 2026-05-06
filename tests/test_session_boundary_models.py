"""Tests for typed session/storage boundary contracts."""

from __future__ import annotations

from langgraph_agent_blueprint.models.events import RuntimeEvent, make_event
from langgraph_agent_blueprint.models.sessions import SessionMetadata
from langgraph_agent_blueprint.models.tools import ToolResult
from langgraph_agent_blueprint.storage.session_storage import SessionStorage


def test_session_metadata_preserves_unknown_runtime_metadata_as_extra():
    record = {
        "session_id": "session_1",
        "project_root": "C:/workspace",
        "provider": "fake",
        "usage": {"total_tokens": 10},
        "graph_finished": True,
    }

    metadata = SessionMetadata.from_record(record)

    assert metadata.session_id == "session_1"
    assert metadata.usage == {"total_tokens": 10}
    assert metadata.extra["graph_finished"] is True


def test_session_storage_validates_events_and_skips_corrupt_jsonl(tmp_path):
    storage = SessionStorage(tmp_path / "storage")
    event = make_event("session_started", "session_1")
    storage.append_event(tmp_path, "session_1", event.model_dump(mode="json"))
    events_path = storage.session_dir(tmp_path, "session_1") / "events.jsonl"
    events_path.write_text(events_path.read_text(encoding="utf-8") + "{not json}\n", encoding="utf-8")

    loaded = storage.load_session(tmp_path, "session_1")

    assert [RuntimeEvent.model_validate(item).type for item in loaded["events"]] == ["session_started"]


def test_session_storage_validates_tool_results_at_jsonl_boundary(tmp_path):
    storage = SessionStorage(tmp_path / "storage")
    result = ToolResult(id="call_1", name="read_file", status="ok", content="hello")

    storage.append_tool_call(tmp_path, "session_1", result.model_dump(mode="json"))
    loaded = storage.load_session(tmp_path, "session_1")

    assert ToolResult.model_validate(loaded["tool_calls"][0]) == result
