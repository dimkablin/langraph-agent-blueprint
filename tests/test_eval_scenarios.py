"""Acceptance coverage for checked-in eval scenarios."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.evals.loader import load_scenarios
from langgraph_agent_blueprint.evals.runner import EvalRunner


def test_checked_in_core_eval_scenarios_pass(tmp_path: Path) -> None:
    scenarios = load_scenarios(Path("evals/scenarios"))
    runner = EvalRunner(report_root=tmp_path / "reports")

    results = [runner.run_scenario(scenario) for scenario in scenarios]

    assert all(result.passed for result in results), {result.scenario_id: result.failures for result in results}
    assert len(results) >= 10
