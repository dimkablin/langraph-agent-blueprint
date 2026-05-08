"""Typed approval/resume API contract tests."""

from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def test_typed_approval_decision_rejects_permission_request(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    first = client.post(
        "/chat",
        json={"message": "tool:write_file frontend-created.txt hello", "thread_id": "typed-approval"},
    ).json()
    permission = first["permission_required"]

    response = client.post(
        "/approval",
        json={
            "thread_id": "typed-approval",
            "session_id": first["session_id"],
            "decision": {
                "tool_call_id": permission["tool_call_id"],
                "decision": "rejected",
                "reason": "typed frontend rejection",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == first["session_id"]
    assert any(
        event["type"] == "permission_resolved" and event["data"]["decision"] == "rejected"
        for event in payload["events"]
    )


def test_approval_rejects_invalid_decision_literal_at_api_boundary(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    response = client.post(
        "/approval",
        json={
            "thread_id": "typed-invalid",
            "decision": {"tool_call_id": "tool-1", "decision": "maybe"},
        },
    )

    assert response.status_code == 422


def test_legacy_approval_shape_remains_supported(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    first = client.post(
        "/chat",
        json={"message": "tool:write_file frontend-created.txt hello", "thread_id": "legacy-approval"},
    ).json()

    response = client.post(
        "/approval",
        json={
            "thread_id": "legacy-approval",
            "session_id": first["session_id"],
            "decision": {"approved": False, "reason": "legacy frontend rejection"},
        },
    )

    assert response.status_code == 200
    assert "rejected" in response.json()["final_response"].lower()

