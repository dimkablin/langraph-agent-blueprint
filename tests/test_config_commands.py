"""Slash and CLI config command coverage."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from langgraph_agent_blueprint.cli import app
from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_slash_config_explain_and_validate(tmp_path: Path) -> None:
    runtime = AssistantGraphRuntime(build_dependencies(AppConfig.from_env(project_root=tmp_path)))

    explain = runtime.invoke("/config explain", input_kind="headless", project_root=tmp_path)
    validate = runtime.invoke("/config validate", input_kind="headless", project_root=tmp_path)

    assert "Sources:" in explain["final_response"]
    assert "model_name" in explain["final_response"]
    assert "Config diagnostics:" in validate["final_response"]


def test_cli_config_show_explain_validate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    show = runner.invoke(app, ["config", "show"])
    explain = runner.invoke(app, ["config", "explain"])
    validate = runner.invoke(app, ["config", "validate"])

    assert show.exit_code == 0
    assert explain.exit_code == 0
    assert validate.exit_code == 0
    assert "llm_provider" in show.output
    assert "Sources:" in explain.output
    assert "Config diagnostics:" in validate.output

