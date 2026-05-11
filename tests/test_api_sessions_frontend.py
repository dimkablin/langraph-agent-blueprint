"""Frontend-facing session endpoint contract tests."""

from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def _create_session(client: TestClient) -> str:
    response = client.post("/chat", json={"message": "hello from session api"})
    assert response.status_code == 200
    return response.json()["session_id"]


def test_sessions_list_and_detail_are_frontend_dtos(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)
    session_id = _create_session(client)

    sessions = client.get("/sessions").json()
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["title"] == "hello from session api"
    assert "message_count" in sessions[0]
    assert "event_count" in sessions[0]

    detail = client.get(f"/sessions/{session_id}").json()
    assert detail["session_id"] == session_id
    assert detail["title"] == "hello from session api"
    assert detail["metadata"]["title"] == "hello from session api"
    assert detail["messages"]
    assert detail["events"]
    assert "context" in detail
    assert "child_runs" in detail
    assert "project_root" not in detail


def test_session_title_is_created_from_first_message_and_preserved(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    first = client.post("/chat", json={"message": "first durable chat title"}).json()
    second = client.post(
        "/chat",
        json={
            "message": "second message should not rename chat",
            "session_id": first["session_id"],
            "thread_id": first["thread_id"],
        },
    )

    assert second.status_code == 200
    detail = client.get(f"/sessions/{first['session_id']}").json()
    assert detail["title"] == "first durable chat title"
    assert detail["metadata"]["title"] == "first durable chat title"


def test_session_persists_model_intelligence_preference(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    response = client.post("/chat", json={"message": "hello", "model_intelligence": "high"})

    assert response.status_code == 200
    detail = client.get(f"/sessions/{response.json()['session_id']}").json()
    assert detail["metadata"]["model_intelligence"] == "high"


def test_session_messages_events_context_and_child_runs_endpoints(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)
    session_id = _create_session(client)

    messages = client.get(f"/sessions/{session_id}/messages").json()
    events = client.get(f"/sessions/{session_id}/events").json()
    context = client.get(f"/sessions/{session_id}/context").json()
    child_runs = client.get(f"/sessions/{session_id}/child-runs").json()

    assert messages[0]["role"] == "human"
    assert any(event["type"] == "final_response" for event in events)
    assert {"references", "fragments", "budget", "errors"} <= set(context)
    assert isinstance(child_runs, list)


def test_session_context_endpoint_returns_resolved_fragment_content(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "README.md").write_text("SESSION_CONTEXT_WINDOW_TOKEN", encoding="utf-8")
    app = create_app(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=project_root,
            cwd=project_root,
            llm_provider="fake",
        )
    )
    client = TestClient(app)

    response = client.post("/chat", json={"message": "Use @README.md"})
    context = client.get(f"/sessions/{response.json()['session_id']}/context").json()

    assert context["references"][0]["value"] == "README.md"
    assert context["fragments"][0]["title"] == "README.md"
    assert context["fragments"][0]["content"] == "SESSION_CONTEXT_WINDOW_TOKEN"
    assert context["budget"]["used_tokens"] > 0


def test_session_message_dtos_hide_internal_compaction_summary(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    first = client.post("/chat", json={"message": "hello before compact"}).json()
    compact = client.post(
        "/chat",
        json={
            "message": "/compact",
            "session_id": first["session_id"],
            "thread_id": first["thread_id"],
        },
    )

    assert compact.status_code == 200
    messages = client.get(f"/sessions/{first['session_id']}/messages").json()
    detail = client.get(f"/sessions/{first['session_id']}").json()

    assert messages
    assert not [message for message in messages if str(message["content"]).startswith("Compacted prior context:")]
    assert not [message for message in detail["messages"] if str(message["content"]).startswith("Compacted prior context:")]


def test_session_export_endpoint_returns_export_record(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)
    session_id = _create_session(client)

    response = client.post(f"/sessions/{session_id}/export", json={"format": "markdown"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert payload["format"] == "markdown"
    assert payload["path"]
