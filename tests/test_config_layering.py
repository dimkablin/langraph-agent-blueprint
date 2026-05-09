"""Config layering and explain diagnostics tests."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig


def test_config_layering_precedence_env_project_user_dotenv_defaults(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("MODEL_NAME=dotenv-model\nNETWORK_ENABLED=false\n", encoding="utf-8")
    user_config = tmp_path / "user-config.toml"
    user_config.write_text('model_name = "user-model"\nnetwork_enabled = true\npermission_mode = "plan"\n', encoding="utf-8")
    project_config = project / ".lg-agent" / "config.toml"
    project_config.parent.mkdir()
    project_config.write_text('model_name = "project-model"\npermission_mode = "strict"\n', encoding="utf-8")

    config, report = AppConfig.load_with_report(
        project_root=project,
        user_config_path=user_config,
        environ={"MODEL_NAME": "env-model"},
        model_name="override-model",
    )

    assert config.model_name == "override-model"
    assert config.permission_mode == "strict"
    assert config.network_enabled is True
    origins = {value.key: value.source for value in report.values}
    assert origins["model_name"] == "override"
    assert origins["permission_mode"] == "project_config"
    assert origins["network_enabled"] == "user_config"
    assert any(source.kind == "dotenv" and source.loaded for source in report.sources)


def test_config_explain_redacts_secrets_and_reports_invalid_values(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    project_config = project / ".lg-agent" / "config.toml"
    project_config.parent.mkdir()
    project_config.write_text('network_enabled = "not-a-bool"\nopenai_api_key = "sk-secret"\n', encoding="utf-8")

    config, report = AppConfig.load_with_report(project_root=project, environ={})

    assert config.network_enabled is False
    values = {value.key: value for value in report.values}
    assert values["openai_api_key"].value_repr == "***"
    assert values["openai_api_key"].redacted is True
    assert any(item.status == "warning" and item.key == "network_enabled" for item in report.diagnostics)


def test_config_redaction_keeps_numeric_context_token_budget_visible(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    config, report = AppConfig.load_with_report(
        project_root=project,
        environ={"CONTEXT_MAX_TOKENS": "12000", "OPENAI_API_KEY": "sk-secret"},
    )

    values = {value.key: value for value in report.values}
    assert config.redacted()["context_max_tokens"] == 12000
    assert values["context_max_tokens"].value_repr == "12000"
    assert values["context_max_tokens"].redacted is False
    assert config.redacted()["openai_api_key"] == "***"
    assert values["openai_api_key"].redacted is True


def test_project_config_supports_observability_langfuse_table(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    project_config = project / ".lg-agent" / "config.toml"
    project_config.parent.mkdir()
    project_config.write_text(
        """
[observability.langfuse]
enabled = true
environment = "ci"
""".strip(),
        encoding="utf-8",
    )

    config, report = AppConfig.load_with_report(project_root=project, environ={})

    assert config.langfuse.enabled is True
    assert config.langfuse.environment == "ci"
    origins = {value.key: value.source for value in report.values}
    assert origins["langfuse"] == "project_config"
