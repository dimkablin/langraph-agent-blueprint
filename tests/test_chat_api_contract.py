"""FastAPI chat route contracts for streaming control endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.routes_chat import router as chat_router
from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.models import RunCancellationResult


@dataclass
class FakeRuntime:
    cancelled: list[dict[str, Any]] = field(default_factory=list)

    def cancel(self, thread_id: str, *, session_id: str | None = None, reason: str | None = None) -> dict[str, Any]:
        payload = {"thread_id": thread_id, "session_id": session_id, "reason": reason}
        self.cancelled.append(payload)
        return {"cancelled": True, **payload}


def test_chat_and_approval_responses_include_top_level_usage(tmp_path: Path) -> None:
    class RuntimeWithUsage:
        dependencies = SimpleNamespace(observability_service=SimpleNamespace(redact_payload=lambda payload: payload))

        def invoke(self, input_text: str, **kwargs: Any) -> dict[str, Any]:
            return {
                "session_id": "session_usage_123",
                "thread_id": "thread_usage_123",
                "final_response": "done",
                "ui_events": [],
                "usage": {"context_used": 12, "context_max": 100, "context_percent": 12},
            }

        def resume(self, thread_id: str, decision: dict[str, Any], *, session_id: str | None = None) -> dict[str, Any]:
            return {
                "session_id": session_id or "session_usage_123",
                "thread_id": thread_id,
                "final_response": "approved",
                "ui_events": [],
                "usage": {"context_used": 18, "context_max": 100, "context_percent": 18},
            }

    app = create_app(AppConfig(storage_dir=tmp_path / ".storage", project_root=tmp_path, cwd=tmp_path))
    app.state.runtime = RuntimeWithUsage()
    client = TestClient(app)

    chat_response = client.post("/chat", json={"message": "hi"})
    approval_response = client.post(
        "/approval",
        json={"thread_id": "thread_usage_123", "session_id": "session_usage_123", "decision": {"approved": True}},
    )

    assert chat_response.status_code == 200
    assert chat_response.json()["usage"] == {"context_used": 12, "context_max": 100, "context_percent": 12}
    assert approval_response.status_code == 200
    assert approval_response.json()["usage"] == {"context_used": 18, "context_max": 100, "context_percent": 18}


def test_chat_cancel_endpoint_delegates_to_runtime_control_service() -> None:
    runtime = FakeRuntime()
    app = FastAPI()
    app.state.runtime = runtime
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.post(
        "/chat/cancel",
        json={
            "thread_id": "thread_stop_123",
            "session_id": "session_stop_123",
            "reason": "stop button",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "cancelled": True,
        "thread_id": "thread_stop_123",
        "session_id": "session_stop_123",
        "reason": "stop button",
    }
    assert runtime.cancelled == [
        {
            "thread_id": "thread_stop_123",
            "session_id": "session_stop_123",
            "reason": "stop button",
        }
    ]


def test_chat_stream_endpoint_delegates_permission_mode_to_runtime() -> None:
    @dataclass
    class RuntimeWithStream:
        stream_calls: list[dict[str, Any]] = field(default_factory=list)
        dependencies: Any = field(
            default_factory=lambda: SimpleNamespace(
                observability_service=SimpleNamespace(redact_payload=lambda payload: payload),
            )
        )

        def stream(self, input_text: str, **kwargs: Any) -> list[dict[str, Any]]:
            self.stream_calls.append({"input_text": input_text, **kwargs})
            return []

    runtime = RuntimeWithStream()
    app = FastAPI()
    app.state.runtime = runtime
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "do it",
            "thread_id": "thread_perm_123",
            "permission_mode": "bypass_read_only",
        },
    )

    assert response.status_code == 200
    assert runtime.stream_calls == [
        {
            "input_text": "do it",
            "input_kind": "headless",
            "project_id": None,
            "session_id": None,
            "thread_id": "thread_perm_123",
            "model_intelligence": None,
            "permission_mode": "bypass_read_only",
            "attachments": [],
        }
    ]


def test_chat_cancel_endpoint_serializes_runtime_cancellation_result() -> None:
    class RuntimeWithTypedResult:
        def cancel(self, thread_id: str, *, session_id: str | None = None, reason: str | None = None) -> RunCancellationResult:
            return RunCancellationResult(
                cancelled=False,
                thread_id=thread_id,
                session_id=session_id,
                reason=reason or "not active",
            )

    app = FastAPI()
    app.state.runtime = RuntimeWithTypedResult()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.post("/chat/cancel", json={"thread_id": "thread_probe_123"})

    assert response.status_code == 200
    assert response.json() == {
        "cancelled": False,
        "thread_id": "thread_probe_123",
        "session_id": None,
        "reason": "not active",
    }
