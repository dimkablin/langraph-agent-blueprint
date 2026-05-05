from fastapi.testclient import TestClient

from claude_code_langgraph.api.server import create_app
from claude_code_langgraph.config import AppConfig


def test_chat_api_returns_frontend_runtime_contract(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["thread_id"]
    assert payload["final_response"] == "Fake response: hello"
    assert payload["events"]


def test_chat_api_exposes_permission_and_approval_resume(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    first = client.post(
        "/chat",
        json={"message": "tool:write_file frontend-created.txt hello", "thread_id": "frontend-permission"},
    ).json()

    assert first["thread_id"] == "frontend-permission"
    assert first["permission_required"]["tool_name"] == "write_file"

    resumed = client.post(
        "/approval",
        json={"thread_id": "frontend-permission", "decision": {"approved": False, "reason": "front-end test"}},
    ).json()

    assert resumed["thread_id"] == "frontend-permission"
    assert "rejected" in resumed["final_response"].lower()

