"""CLI tests for eval list/run commands."""

from __future__ import annotations

from typer.testing import CliRunner

from langgraph_agent_blueprint.cli import app


def test_eval_cli_list_shows_builtin_scenarios() -> None:
    result = CliRunner().invoke(app, ["eval", "list"])

    assert result.exit_code == 0
    assert "basic-chat" in result.output
    assert "mcp-echo" in result.output


def test_eval_cli_run_named_scenario_writes_report(tmp_path) -> None:
    result = CliRunner().invoke(app, ["eval", "run", "basic-chat", "--report-dir", str(tmp_path / "reports")])

    assert result.exit_code == 0
    assert "basic-chat" in result.output
    assert "passed" in result.output.lower()
