"""Pydantic boundary tests for real subagent runtime models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.models.subagents import ChildRunMetadata, SubagentRequest, SubagentResult


def test_subagent_request_validates_prompt_and_limits() -> None:
    request = SubagentRequest(
        prompt="Inspect permissions.",
        name="repo-investigator",
        allowed_tools=["read_file", "grep"],
        max_turns=4,
        timeout_seconds=30,
    )

    assert request.prompt == "Inspect permissions."
    assert request.allowed_tools == ["read_file", "grep"]


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": ""},
        {"prompt": "   "},
        {"prompt": "ok", "max_turns": 0},
        {"prompt": "ok", "max_turns": 101},
        {"prompt": "ok", "timeout_seconds": 0},
    ],
)
def test_subagent_request_rejects_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SubagentRequest.model_validate(payload)


def test_child_run_metadata_and_result_are_json_safe() -> None:
    metadata = ChildRunMetadata(
        child_run_id="child_abc123",
        parent_session_id="session_parent",
        parent_thread_id="thread_parent",
        child_session_id="session_child",
        child_thread_id="thread_child",
        name="reader",
        purpose="Read one file",
        status="completed",
        started_at="2026-05-07T00:00:00+00:00",
        completed_at="2026-05-07T00:00:01+00:00",
    )
    result = SubagentResult(
        child_run_id=metadata.child_run_id,
        status="ok",
        summary="Read complete.",
        final_response="Tool read_file ok: hello",
    )

    dumped = {"metadata": metadata.model_dump(mode="json"), "result": result.model_dump(mode="json")}

    assert dumped["metadata"]["child_session_id"] == "session_child"
    assert dumped["result"]["status"] == "ok"

