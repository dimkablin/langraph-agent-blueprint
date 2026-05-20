"""P0 tests for cooperative runtime cancellation."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from langgraph_agent_blueprint.models import ModelResponse, ModelStreamEvent, Usage

from .helpers import recording_shell_executor


class CancellingStreamingToolModel:
    def __init__(self, thread_id: str) -> None:
        self.thread_id = thread_id
        self.run_control: Any | None = None

    def generate(self, request: Any) -> ModelResponse:
        raise AssertionError("Cancellation during streaming must not fall back to non-streaming generation.")

    def stream_generate(self, request: Any) -> list[ModelStreamEvent]:
        assert self.run_control is not None
        self.run_control.cancel(self.thread_id, reason="stop button")
        tool_call = {
            "id": "cancelled_shell",
            "name": "bash",
            "args": {"command": "Write-Output should-not-run"},
        }
        return [
            ModelStreamEvent(
                type="response",
                response=ModelResponse(
                    content="",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="", tool_calls=[tool_call]),
                    usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            )
        ]


def test_stream_cancellation_stops_before_tool_routing(
    runtime_factory,
    approving_permissions,
    temp_project,
) -> None:
    thread_id = "thread_stop_runtime_123"
    model = CancellingStreamingToolModel(thread_id)
    shell = recording_shell_executor()
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=model,
        permissions=approving_permissions,
        shell_executor=shell,
    )
    model.run_control = runtime.dependencies.run_control_service

    events = list(
        runtime.stream(
            "Run a command and then stop.",
            project_root=temp_project,
            thread_id=thread_id,
            session_id="session_stop_runtime_123",
        )
    )

    assert shell.executed_commands == []
    assert [item["type"] for item in events if item["type"] in {"run_cancelled", "final_response"}] == [
        "run_cancelled",
        "final_response",
    ]
