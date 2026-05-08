"""Scenario loader tests for YAML/JSON eval files."""

from __future__ import annotations

from pathlib import Path

import pytest

from langgraph_agent_blueprint.evals.loader import load_scenario, load_scenarios
from langgraph_agent_blueprint.models.evals import EvalScenario


def test_load_yaml_scenario_validates_with_pydantic(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        """
id: loader-basic
description: loader test
steps:
  - input:
      text: hello
    expect:
      events:
        - type: final_response
""".strip(),
        encoding="utf-8",
    )

    scenario = load_scenario(scenario_path)

    assert isinstance(scenario, EvalScenario)
    assert scenario.id == "loader-basic"


def test_load_malformed_scenario_fails_cleanly(tmp_path: Path) -> None:
    scenario_path = tmp_path / "bad.yaml"
    scenario_path.write_text("id: bad\ndescription: missing steps\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid eval scenario"):
        load_scenario(scenario_path)


def test_load_scenarios_sorts_by_id(tmp_path: Path) -> None:
    for name in ["b", "a"]:
        (tmp_path / f"{name}.yaml").write_text(f"id: {name}\ndescription: {name}\nsteps:\n- input:\n    text: hello\n", encoding="utf-8")

    scenarios = load_scenarios(tmp_path)

    assert [scenario.id for scenario in scenarios] == ["a", "b"]
