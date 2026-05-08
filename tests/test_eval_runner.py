"""Eval runner tests proving scenarios execute through the real graph runtime."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.evals.loader import load_scenario
from langgraph_agent_blueprint.evals.runner import EvalRunner


def test_eval_runner_invokes_real_graph_and_writes_report(tmp_path: Path) -> None:
    runner = EvalRunner(report_root=tmp_path / "reports")
    scenario = load_scenario(Path("evals/scenarios/basic-chat.yaml"))

    result = runner.run_scenario(scenario)

    assert result.passed is True
    assert any(event["type"] == "final_response" for event in result.events)
    assert result.metadata["report_json"].endswith("basic-chat.json")
    assert Path(result.metadata["report_json"]).exists()
    assert Path(result.metadata["report_md"]).exists()


def test_eval_runner_ignores_local_env_and_uses_temp_workspace_storage(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".env").write_text("LLM_PROVIDER=ollama\nNETWORK_ENABLED=true\n", encoding="utf-8")
    scenario = load_scenario(Path("evals/scenarios/basic-chat.yaml")).model_copy(update={"workspace_fixture": None})
    runner = EvalRunner(report_root=tmp_path / "reports", workspace_root=workspace)

    result = runner.run_scenario(scenario)

    assert result.passed is True
    assert result.metadata["provider"] == "fake"
    assert Path(result.metadata["storage_dir"]).is_relative_to(tmp_path / "reports")


def test_eval_runner_handles_permission_rejection_without_side_effect(tmp_path: Path) -> None:
    runner = EvalRunner(report_root=tmp_path / "reports")
    scenario = load_scenario(Path("evals/scenarios/write-permission-reject.yaml"))

    result = runner.run_scenario(scenario)

    assert result.passed is True
    assert not (Path(result.metadata["workspace"]) / "blocked.txt").exists()


def test_eval_runner_core_fixture_scenarios_pass(tmp_path: Path) -> None:
    runner = EvalRunner(report_root=tmp_path / "reports")
    ids = ["read-file-context", "mcp-echo", "subagent-readonly", "superpowers-brainstorming"]

    results = [runner.run_scenario(load_scenario(Path(f"evals/scenarios/{scenario_id}.yaml"))) for scenario_id in ids]

    assert all(result.passed for result in results), [result.failures for result in results]
