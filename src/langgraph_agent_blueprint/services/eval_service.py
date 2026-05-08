"""High-level eval/replay service facade for CLI commands."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.evals.loader import load_scenario_by_id, load_scenarios
from langgraph_agent_blueprint.evals.runner import EvalRunner
from langgraph_agent_blueprint.models.evals import EvalRunResult, EvalScenario


class EvalService:
    """Load scenarios and execute them with the real graph runtime."""

    def __init__(self, *, scenarios_dir: str | Path | None = None, report_root: str | Path | None = None) -> None:
        self.scenarios_dir = Path(scenarios_dir) if scenarios_dir is not None else None
        self.report_root = Path(report_root) if report_root is not None else None

    def list_scenarios(self) -> list[EvalScenario]:
        return load_scenarios(self.scenarios_dir)

    def load_scenario(self, scenario_id: str) -> EvalScenario:
        return load_scenario_by_id(scenario_id, self.scenarios_dir)

    def run_scenario(self, scenario_id: str) -> EvalRunResult:
        scenario = self.load_scenario(scenario_id)
        return EvalRunner(report_root=self.report_root).run_scenario(scenario)

    def run_all(self) -> list[EvalRunResult]:
        runner = EvalRunner(report_root=self.report_root)
        return [runner.run_scenario(scenario) for scenario in self.list_scenarios()]
