"""Assertion engine tests for eval/replay reports."""

from __future__ import annotations

from langgraph_agent_blueprint.evals.assertions import EvalAssertionEngine
from langgraph_agent_blueprint.models.evals import EvalExpectations


def test_assertions_match_events_tool_calls_and_final_response() -> None:
    result = {
        "ui_events": [
            {"type": "tool_call_finished", "data": {"name": "read_file", "status": "ok"}},
            {"type": "final_response", "data": {"content": "README summary"}},
        ],
        "tool_results": [{"name": "read_file", "status": "ok", "content": "README"}],
        "final_response": "README summary",
    }
    expectations = EvalExpectations.model_validate(
        {
            "events": [{"type": "tool_call_finished", "contains": {"name": "read_file"}}],
            "tool_calls": [{"name": "read_file", "status": "ok"}],
            "final_response": {"contains": ["README"], "not_contains": ["Traceback"]},
        }
    )

    failures = EvalAssertionEngine().assert_expectations(result, expectations)

    assert failures == []


def test_assertions_report_missing_context_fragment() -> None:
    result = {"ui_events": [], "resolved_context": [], "final_response": ""}
    expectations = EvalExpectations.model_validate(
        {"context_fragments": [{"kind": "file", "title_contains": "README", "trust": "trusted_local"}]}
    )

    failures = EvalAssertionEngine().assert_expectations(result, expectations)

    assert failures
    assert "context fragment" in failures[0]
