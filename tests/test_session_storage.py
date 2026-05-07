"""Regression tests for session/thread identifier storage boundaries."""

from __future__ import annotations

import pytest

from langgraph_agent_blueprint.graph.state import create_initial_state
from langgraph_agent_blueprint.storage.session_storage import SessionStorage
from langgraph_agent_blueprint.utils.ids import new_id, validate_session_id, validate_thread_id


@pytest.mark.parametrize(
    "bad_id",
    [
        "",
        "../evil",
        "..\\evil",
        "/tmp/evil",
        "C:\\tmp\\evil",
        "C:evil",
        "a/b",
        "a\\b",
        "x" * 129,
    ],
)
def test_session_ids_reject_path_syntax(bad_id: str) -> None:
    with pytest.raises(ValueError):
        validate_session_id(bad_id)


@pytest.mark.parametrize("valid_id", [new_id("session"), "session_abc-123", "thread-123_ABC"])
def test_session_ids_accept_runtime_identifier_shape(valid_id: str) -> None:
    assert validate_session_id(valid_id) == valid_id
    assert validate_thread_id(valid_id) == valid_id


def test_storage_rejects_invalid_session_id_before_path_creation(tmp_path) -> None:
    storage = SessionStorage(tmp_path / "storage")

    with pytest.raises(ValueError):
        storage.create_session(tmp_path, "../evil", {})

    assert not (tmp_path / "storage" / "projects").exists()


def test_storage_session_dir_is_confined_under_sessions_root(tmp_path) -> None:
    storage = SessionStorage(tmp_path / "storage")

    session_dir = storage.session_dir(tmp_path, "session_abc-123")
    sessions_root = session_dir.parent.resolve()

    assert session_dir.resolve().is_relative_to(sessions_root)
    assert session_dir.name == "session_abc-123"


def test_initial_state_rejects_invalid_supplied_ids(tmp_path) -> None:
    with pytest.raises(ValueError):
        create_initial_state("hello", project_root=tmp_path, session_id="../evil")

    with pytest.raises(ValueError):
        create_initial_state("hello", project_root=tmp_path, thread_id="a/b")
