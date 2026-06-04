from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def client_at(tmp_path: Path) -> TestClient:
    return TestClient(create_app(AppConfig(storage_dir=tmp_path / ".storage", project_root=tmp_path, cwd=tmp_path)))


def test_conversation_api_scopes_list_get_and_mutations_to_current_user(tmp_path):
    client = client_at(tmp_path)
    created = client.post("/conversations", headers={"X-User-Id": "user-a"}, json={"title": "Private"})
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]

    assert client.get("/conversations", headers={"X-User-Id": "user-b"}).json() == []
    forbidden_get = client.get(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-b"})
    assert forbidden_get.status_code == 404
    forbidden_rename = client.patch(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-b"}, json={"title": "Stolen"})
    assert forbidden_rename.status_code == 404

    renamed = client.patch(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-a"}, json={"title": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"

    archived = client.post(f"/conversations/{conversation_id}/archive", headers={"X-User-Id": "user-a"})
    assert archived.status_code == 200
    assert client.get("/conversations", headers={"X-User-Id": "user-a"}).json() == []
    assert len(client.get("/conversations?include_archived=true", headers={"X-User-Id": "user-a"}).json()) == 1

    deleted = client.delete(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-a"})
    assert deleted.status_code == 204
    assert client.get(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-a"}).status_code == 404


def test_chat_endpoint_creates_and_appends_user_scoped_conversation_history(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / ".storage", project_root=tmp_path, cwd=tmp_path))
    dependencies = app.state.runtime.dependencies

    class RuntimeWithConversationDependencies:
        def __init__(self) -> None:
            self.dependencies = dependencies
            self.calls: list[dict[str, Any]] = []

        def invoke(self, input_text: str, **kwargs: Any) -> dict[str, Any]:
            self.calls.append({"input_text": input_text, **kwargs})
            session_id = kwargs.get("session_id") or "session_chat_123"
            thread_id = kwargs.get("thread_id") or session_id
            return {
                "session_id": session_id,
                "thread_id": thread_id,
                "final_response": "assistant answer",
                "ui_events": [
                    {
                        "id": "event_chat_1",
                        "type": "final_response",
                        "timestamp": "2026-01-01T00:00:00Z",
                        "session_id": session_id,
                        "data": {"content": "assistant answer"},
                    }
                ],
                "usage": {},
            }

    runtime = RuntimeWithConversationDependencies()
    app.state.runtime = runtime
    client = TestClient(app)

    response = client.post("/chat", headers={"X-User-Id": "user-a"}, json={"message": "hello"})

    assert response.status_code == 200
    conversation_id = response.json()["session_id"]
    assert runtime.calls[0]["session_id"] == conversation_id
    assert runtime.calls[0]["thread_id"] == conversation_id
    detail = client.get(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-a"})
    assert detail.status_code == 200
    assert [(message["role"], message["content"]) for message in detail.json()["messages"]] == [
        ("user", "hello"),
        ("assistant", "assistant answer"),
    ]
    assert client.get(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-b"}).status_code == 404


def test_chat_endpoint_uses_conversation_thread_identity_instead_of_client_thread_id(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / ".storage", project_root=tmp_path, cwd=tmp_path))
    dependencies = app.state.runtime.dependencies

    class RuntimeWithConversationDependencies:
        def __init__(self) -> None:
            self.dependencies = dependencies
            self.calls: list[dict[str, Any]] = []

        def invoke(self, input_text: str, **kwargs: Any) -> dict[str, Any]:
            self.calls.append({"input_text": input_text, **kwargs})
            return {
                "session_id": kwargs["session_id"],
                "thread_id": kwargs["thread_id"],
                "final_response": "assistant answer",
                "ui_events": [],
                "usage": {},
            }

    runtime = RuntimeWithConversationDependencies()
    app.state.runtime = runtime
    client = TestClient(app)

    response = client.post(
        "/chat",
        headers={"X-User-Id": "user-a"},
        json={"message": "hello", "thread_id": "client_generated_thread"},
    )

    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]
    assert runtime.calls[0]["session_id"] == conversation_id
    assert runtime.calls[0]["thread_id"] == conversation_id
    assert response.json()["thread_id"] == conversation_id


def test_chat_stream_endpoint_creates_and_persists_conversation_history(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / ".storage", project_root=tmp_path, cwd=tmp_path))
    dependencies = app.state.runtime.dependencies

    class RuntimeWithConversationStream:
        def __init__(self) -> None:
            self.dependencies = dependencies
            self.calls: list[dict[str, Any]] = []

        def stream(self, input_text: str, **kwargs: Any) -> list[dict[str, Any]]:
            self.calls.append({"input_text": input_text, **kwargs})
            session_id = kwargs["session_id"]
            return [
                {
                    "id": "event_stream_1",
                    "type": "final_response",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "session_id": session_id,
                    "data": {"content": "stream answer"},
                }
            ]

    runtime = RuntimeWithConversationStream()
    app.state.runtime = runtime
    client = TestClient(app)

    response = client.post(
        "/chat/stream",
        headers={"X-User-Id": "user-a"},
        json={"message": "stream hello", "thread_id": "client_generated_thread"},
    )

    assert response.status_code == 200
    conversation_id = runtime.calls[0]["session_id"]
    assert runtime.calls[0]["thread_id"] == conversation_id
    assert f'"thread_id":"{conversation_id}"' in response.text
    detail = client.get(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-a"}).json()
    assert [(message["role"], message["content"]) for message in detail["messages"]] == [
        ("user", "stream hello"),
        ("assistant", "stream answer"),
    ]
    assert [event["event_id"] for event in detail["events"]] == ["event_stream_1"]


def test_append_message_endpoint_persists_user_and_assistant_messages_idempotently(tmp_path):
    client = client_at(tmp_path)
    created = client.post("/conversations", headers={"X-User-Id": "user-a"}, json={"title": "Append"}).json()
    conversation_id = created["conversation_id"]

    for _ in range(2):
        response = client.post(
            f"/conversations/{conversation_id}/messages",
            headers={"X-User-Id": "user-a"},
            json={
                "user_message": {"role": "user", "content": "hello", "idempotency_key": "turn-1:user"},
                "assistant_message": {"role": "assistant", "content": "hi", "idempotency_key": "turn-1:assistant"},
                "events": [{"event_id": "event-1", "type": "final", "payload": {"ok": True}}],
            },
        )
        assert response.status_code == 200

    detail = client.get(f"/conversations/{conversation_id}", headers={"X-User-Id": "user-a"}).json()
    assert [(message["role"], message["content"]) for message in detail["messages"]] == [("user", "hello"), ("assistant", "hi")]
    assert [event["event_id"] for event in detail["events"]] == ["event-1"]


def test_approval_and_cancel_require_owned_conversation(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / ".storage", project_root=tmp_path, cwd=tmp_path))
    dependencies = app.state.runtime.dependencies

    class RuntimeWithApprovalAndCancel:
        def __init__(self) -> None:
            self.dependencies = dependencies
            self.resume_calls: list[dict[str, Any]] = []
            self.cancel_calls: list[dict[str, Any]] = []

        def resume(self, thread_id: str, decision: dict[str, Any], *, session_id: str | None = None) -> dict[str, Any]:
            self.resume_calls.append({"thread_id": thread_id, "decision": decision, "session_id": session_id})
            return {
                "session_id": session_id or thread_id,
                "thread_id": thread_id,
                "final_response": "approved answer",
                "ui_events": [
                    {
                        "id": "event_approval_1",
                        "type": "final_response",
                        "timestamp": "2026-01-01T00:00:00Z",
                        "session_id": session_id or thread_id,
                        "data": {"content": "approved answer"},
                    }
                ],
                "usage": {},
            }

        def cancel(self, thread_id: str, *, session_id: str | None = None, reason: str | None = None) -> dict[str, Any]:
            self.cancel_calls.append({"thread_id": thread_id, "session_id": session_id, "reason": reason})
            return {"cancelled": True, "thread_id": thread_id, "session_id": session_id, "reason": reason}

    app.state.runtime = RuntimeWithApprovalAndCancel()
    client = TestClient(app)
    created = client.post("/conversations", headers={"X-User-Id": "user-a"}, json={"title": "Approval"}).json()

    approval_payload = {"thread_id": created["thread_id"], "session_id": created["session_id"], "decision": {"approved": True}}
    assert client.post("/approval", json=approval_payload).status_code == 401
    assert client.post("/approval", headers={"X-User-Id": "user-b"}, json=approval_payload).status_code == 404
    assert client.post("/approval/events", headers={"X-User-Id": "user-b"}, json=approval_payload).status_code == 404
    assert client.post("/chat/cancel", headers={"X-User-Id": "user-b"}, json={"thread_id": created["thread_id"], "session_id": created["session_id"]}).status_code == 404

    approval = client.post("/approval", headers={"X-User-Id": "user-a"}, json=approval_payload)
    assert approval.status_code == 200
    cancel = client.post("/chat/cancel", headers={"X-User-Id": "user-a"}, json={"thread_id": created["thread_id"], "session_id": created["session_id"], "reason": "stop"})
    assert cancel.status_code == 200


def test_approval_resume_persists_answer_and_events_for_history_reload(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path / ".storage", project_root=tmp_path, cwd=tmp_path))
    dependencies = app.state.runtime.dependencies

    class RuntimeWithApprovalHistory:
        def __init__(self) -> None:
            self.dependencies = dependencies

        def resume(self, thread_id: str, decision: dict[str, Any], *, session_id: str | None = None) -> dict[str, Any]:
            return {
                "session_id": session_id or thread_id,
                "thread_id": thread_id,
                "final_response": "approval final answer",
                "ui_events": [
                    {
                        "id": "event_approval_history",
                        "type": "final_response",
                        "timestamp": "2026-01-01T00:00:00Z",
                        "session_id": session_id or thread_id,
                        "data": {"content": "approval final answer"},
                    }
                ],
                "usage": {},
            }

    app.state.runtime = RuntimeWithApprovalHistory()
    client = TestClient(app)
    created = client.post("/conversations", headers={"X-User-Id": "user-a"}, json={"title": "Approval history"}).json()
    response = client.post(
        "/approval",
        headers={"X-User-Id": "user-a"},
        json={"thread_id": created["thread_id"], "session_id": created["session_id"], "decision": {"approved": True}},
    )
    assert response.status_code == 200

    reloaded = TestClient(app).get(f"/conversations/{created['conversation_id']}", headers={"X-User-Id": "user-a"})
    assert reloaded.status_code == 200
    assert [(message["role"], message["content"]) for message in reloaded.json()["messages"]] == [("assistant", "approval final answer")]
    assert [event["event_id"] for event in reloaded.json()["events"]] == ["event_approval_history"]
