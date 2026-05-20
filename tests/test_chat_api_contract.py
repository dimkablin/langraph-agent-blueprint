"""FastAPI chat route contracts for streaming control endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.routes_chat import router as chat_router


@dataclass
class FakeRuntime:
    cancelled: list[dict[str, Any]] = field(default_factory=list)

    def cancel(self, thread_id: str, *, session_id: str | None = None, reason: str | None = None) -> dict[str, Any]:
        payload = {"thread_id": thread_id, "session_id": session_id, "reason": reason}
        self.cancelled.append(payload)
        return {"cancelled": True, **payload}


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
