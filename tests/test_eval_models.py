"""Pydantic boundary tests for eval/replay scenario models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.models.evals import EvalScenario, EvalStep


def test_eval_scenario_validates_nested_expectations() -> None:
    scenario = EvalScenario.model_validate(
        {
            "id": "basic-chat",
            "description": "basic deterministic chat",
            "steps": [
                {
                    "input": {"text": "hello"},
                    "expect": {
                        "events": [{"type": "final_response"}],
                        "final_response": {"contains": ["Fake response"]},
                    },
                }
            ],
        }
    )

    assert scenario.provider == "fake"
    assert scenario.steps[0].expect.events[0].type == "final_response"


def test_eval_scenario_rejects_empty_steps() -> None:
    with pytest.raises(ValidationError):
        EvalScenario.model_validate({"id": "empty", "description": "bad", "steps": []})


def test_eval_step_supports_permission_resume_payload() -> None:
    step = EvalStep.model_validate(
        {
            "input": {
                "text": "tool:write_file out.txt no",
                "approve": False,
                "resume_payload": {"reason": "eval reject"},
            }
        }
    )

    assert step.input.approve is False
    assert step.input.resume_payload == {"reason": "eval reject"}
