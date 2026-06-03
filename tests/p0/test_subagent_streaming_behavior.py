"""P0 streaming coverage for subagent ReAct visibility."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from langgraph_agent_blueprint.models import ModelRequest, ModelResponse, ModelStreamEvent, Usage


class StreamingTwoSubagentsModel:
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("Streaming runtime must not fall back to non-streaming generation.")

    def stream_generate(self, request: ModelRequest) -> list[ModelStreamEvent]:
        text = _latest_human_text(request)
        tool_result_count = _tool_result_count(request)
        if tool_result_count >= 2:
            return _text_response("Both subagents finished.")
        if text == "Build backend":
            return _text_response("Backend subagent done.")
        if text == "Build frontend":
            return _text_response("Frontend subagent done.")
        tool_calls = [
            {
                "id": "backend_agent",
                "name": "agent",
                "args": {"prompt": "Build backend", "name": "backend", "max_turns": 2},
            },
            {
                "id": "frontend_agent",
                "name": "agent",
                "args": {"prompt": "Build frontend", "name": "frontend", "max_turns": 2},
            },
        ]
        return [
            ModelStreamEvent(type="token", token="Now create two agents:"),
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="Now create two agents:",
                    tool_calls=tool_calls,
                    raw=AIMessage(content="Now create two agents:", tool_calls=tool_calls),
                    usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            ),
        ]


def test_stream_forwards_each_subagent_run_and_child_tokens(runtime_factory, approving_permissions, temp_project) -> None:
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=StreamingTwoSubagentsModel(),
        permissions=approving_permissions,
    )

    events = list(
        runtime.stream(
            "Create backend and frontend subagents.",
            project_root=temp_project,
            thread_id="thread_subagent_stream_123",
            session_id="session_subagent_stream_123",
        )
    )

    event_types = [item["type"] for item in events]
    started = [item for item in events if item["type"] == "subagent_started"]
    finished = [item for item in events if item["type"] == "subagent_finished"]
    child_token_events = [
        item
        for item in events
        if item["type"] == "subagent_event" and item.get("data", {}).get("child_event_type") == "model_token"
    ]

    assert event_types.index("model_token") < event_types.index("subagent_started")
    assert [item["data"]["name"] for item in started] == ["backend", "frontend"]
    assert [item["data"]["name"] for item in finished] == ["backend", "frontend"]
    assert len(child_token_events) >= 2
    assert event_types.count("subagent_started") == 2
    assert event_types.count("subagent_finished") == 2
    assert any(item["type"] == "final_response" and item["data"].get("content") == "Both subagents finished." for item in events)


def _text_response(content: str) -> list[ModelStreamEvent]:
    return [
        ModelStreamEvent(type="token", token=content),
        ModelStreamEvent(
            type="response",
            response=ModelResponse(
                content=content,
                raw=AIMessage(content=content),
                usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            ),
        ),
    ]


def _latest_human_text(request: ModelRequest) -> str:
    for message in reversed(request.messages):
        if getattr(message, "type", "") == "human":
            return str(getattr(message, "content", ""))
    return ""


def _tool_result_count(request: ModelRequest) -> int:
    return sum(1 for message in request.messages if getattr(message, "type", "") == "tool")
