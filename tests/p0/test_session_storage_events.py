from __future__ import annotations

import json

from langgraph_agent_blueprint.models import event
from langgraph_agent_blueprint.storage import SessionStorage


def _line_count(path):
    if not path.exists():
        return 0
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


def test_append_events_deduplicates_within_and_across_calls(tmp_path):
    storage = SessionStorage(tmp_path / "storage")
    project_root = tmp_path / "project"
    session_id = "session-dedup"

    first = event("node_finished", session_id=session_id, node="graph", data={"step": "first"})
    first["id"] = "evt-alpha"
    duplicate_within_call = first.copy()
    second = event("node_finished", session_id=session_id, node="graph", data={"step": "second"})
    second["id"] = "evt-beta"
    duplicate_from_retry = first.copy()
    duplicate_from_retry["id"] = "evt-alpha"

    storage.append_events(project_root, session_id, [first, duplicate_within_call, second])

    events_path = storage.session_dir(project_root, session_id) / "events.jsonl"
    index_path = storage.session_dir(project_root, session_id) / "events.index.json"
    assert _line_count(events_path) == 2
    assert set(json.loads(index_path.read_text(encoding="utf-8"))) == {"evt-alpha", "evt-beta"}

    third = event("node_finished", session_id=session_id, node="graph", data={"step": "third"})
    third["id"] = "evt-gamma"
    storage.append_events(project_root, session_id, [duplicate_from_retry, third])

    assert _line_count(events_path) == 3
    assert set(json.loads(index_path.read_text(encoding="utf-8"))) == {"evt-alpha", "evt-beta", "evt-gamma"}


def test_append_events_backfills_missing_index_for_legacy_session(tmp_path):
    storage = SessionStorage(tmp_path / "storage")
    project_root = tmp_path / "project"
    session_id = "legacy-session"
    existing = event("node_finished", session_id=session_id, node="graph", data={"step": "first"})
    existing["id"] = "evt-alpha"
    session_dir = storage.create_session(project_root, session_id, {})
    events_path = session_dir / "events.jsonl"
    index_path = session_dir / "events.index.json"
    events_path.write_text(json.dumps(existing) + "\n", encoding="utf-8")
    index_path.unlink(missing_ok=True)

    storage.append_events(project_root, session_id, [existing])

    assert _line_count(events_path) == 1
    assert set(json.loads(index_path.read_text(encoding="utf-8"))) == {"evt-alpha"}


def test_clear_session_resets_event_index(tmp_path):
    storage = SessionStorage(tmp_path / "storage")
    project_root = tmp_path / "project"
    session_id = "session-clear"

    storage.append_events(
        project_root,
        session_id,
        [event("memory_updated", session_id=session_id, node="graph", data={"value": 1})],
    )
    index_path = storage.session_dir(project_root, session_id) / "events.index.json"
    assert json.loads(index_path.read_text(encoding="utf-8"))

    storage.clear_session(project_root, session_id)

    assert json.loads(index_path.read_text(encoding="utf-8")) == []
