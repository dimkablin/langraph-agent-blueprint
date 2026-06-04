"""Regression coverage for subagent promise-only model responses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.nodes.model_call import model_call_node
from langgraph_agent_blueprint.models import ModelRequest, ModelResponse, Usage


class PromiseOnlySubagentProvider:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return ModelResponse(
                content="Контракт исправлен. Теперь создаю двух саб-агентов:",
                usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            )
        return ModelResponse(
            tool_calls=[
                {
                    "id": "call_backend",
                    "name": "agent",
                    "args": {"name": "backend", "prompt": "Implement the FastAPI backend."},
                },
                {
                    "id": "call_frontend",
                    "name": "agent",
                    "args": {"name": "frontend", "prompt": "Implement the React frontend."},
                },
            ],
            usage=Usage(input_tokens=2, output_tokens=2, total_tokens=4, tool_calls=2),
        )


class PlainTextProvider:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(content="Готово.")


def test_model_call_repairs_subagent_promise_without_tool_calls(tmp_path: Path) -> None:
    deps = build_dependencies(_config(tmp_path))
    provider = PromiseOnlySubagentProvider()
    deps.model_provider = provider  # type: ignore[assignment]

    update = model_call_node(_state(tmp_path), deps)

    assert len(provider.requests) == 2
    assert any(isinstance(message, SystemMessage) for message in provider.requests[1].messages)
    assert update["final_response"] is None
    assert [call["name"] for call in update["pending_tool_calls"]] == ["agent", "agent"]
    assert update["messages"][0].content == "Контракт исправлен. Теперь создаю двух саб-агентов:"
    assert [call["name"] for call in update["messages"][0].tool_calls] == ["agent", "agent"]


def test_model_call_does_not_repair_plain_final_text(tmp_path: Path) -> None:
    deps = build_dependencies(_config(tmp_path))
    provider = PlainTextProvider()
    deps.model_provider = provider  # type: ignore[assignment]

    update = model_call_node(_state(tmp_path), deps)

    assert len(provider.requests) == 1
    assert update["final_response"] == "Готово."
    assert update["pending_tool_calls"] == []


def test_model_call_trims_old_history_before_provider_request(tmp_path: Path) -> None:
    deps = build_dependencies(
        AppConfig(
            llm_provider="fake",
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            plugin_paths=[],
            skills_paths=[],
            context_max_tokens=120,
        )
    )
    provider = PlainTextProvider()
    deps.model_provider = provider  # type: ignore[assignment]
    state = {
        **_state(tmp_path),
        "messages": [
            HumanMessage(content="old user " + ("x" * 1200)),
            AIMessage(content="old assistant " + ("y" * 1200)),
            HumanMessage(content="current question"),
        ],
        "available_tools": {},
        "context_status": {"system_context": "short system"},
    }

    update = model_call_node(state, deps)

    assert [message.content for message in provider.requests[0].messages] == ["current question"]
    usage = update["usage"]
    assert usage["context_used"] <= usage["context_max"]
    assert usage["context_truncated"] is True
    model_context = update["metadata"]["model_context"]
    assert model_context["truncated"] is True
    message_parts = [part for part in model_context["parts"] if part["kind"] == "messages"]
    assert message_parts == [
        {
            "kind": "messages",
            "title": "Message 1",
            "content": "current question",
            "token_estimate": 4,
            "included": True,
            "truncated": False,
            "metadata": {"role": "human"},
        }
    ]


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        llm_provider="fake",
        storage_dir=tmp_path / "storage",
        project_root=tmp_path,
        cwd=tmp_path,
        plugin_paths=[],
        skills_paths=[],
    )


def _state(tmp_path: Path) -> dict[str, Any]:
    deps = build_dependencies(_config(tmp_path))
    return {
        "session_id": "session_subagent_guard",
        "thread_id": "thread_subagent_guard",
        "project_root": str(tmp_path),
        "cwd": str(tmp_path),
        "messages": [
            HumanMessage(
                content="создай два саб-агента которые будут делать фронт на реакте и бек на фастапи только сначала поправь контракт"
            )
        ],
        "available_tools": deps.tool_registry.snapshot(),
        "context_status": {"system_context": ""},
        "metadata": {},
        "usage": {},
        "pending_tool_calls": [],
        "final_response": None,
    }
