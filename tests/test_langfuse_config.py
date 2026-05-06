"""Langfuse config loading and redaction coverage."""

from __future__ import annotations

from langgraph_agent_blueprint.config import AppConfig


def test_langfuse_env_loading_prefers_base_url_over_host(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setenv("LANGFUSE_HOST", "https://host.example")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://base.example")
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "staging")
    monkeypatch.setenv("LANGFUSE_RELEASE", "local")
    monkeypatch.setenv("LANGFUSE_TRACE_USER_ID", "user-1")
    monkeypatch.setenv("LANGFUSE_DEBUG", "true")
    monkeypatch.setenv("LANGFUSE_CAPTURE_INPUTS", "false")
    monkeypatch.setenv("LANGFUSE_CAPTURE_OUTPUTS", "false")
    monkeypatch.setenv("LANGFUSE_RUNTIME_EVENTS_MODE", "metadata_only")

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.langfuse.enabled is True
    assert config.langfuse.public_key == "pk-lf-test"
    assert config.langfuse.secret_key == "sk-lf-test"
    assert config.langfuse.base_url == "https://base.example"
    assert config.langfuse.environment == "staging"
    assert config.langfuse.release == "local"
    assert config.langfuse.trace_user_id == "user-1"
    assert config.langfuse.debug is True
    assert config.langfuse.capture_inputs is False
    assert config.langfuse.capture_outputs is False
    assert config.langfuse.runtime_events_mode == "metadata_only"


def test_langfuse_tracing_environment_alias(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "ci")

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.langfuse.environment == "ci"


def test_process_langfuse_alias_beats_dotenv_preferred_key(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text("LANGFUSE_ENVIRONMENT=dev\n", encoding="utf-8")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "ci")

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.langfuse.environment == "ci"


def test_process_langfuse_preferred_key_beats_process_alias(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "prod")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "ci")

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.langfuse.environment == "prod"


def test_dotenv_langfuse_preferred_key_beats_dotenv_alias(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("LANGFUSE_ENVIRONMENT", raising=False)
    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    (tmp_path / ".env").write_text(
        "LANGFUSE_ENVIRONMENT=dev\nLANGFUSE_TRACING_ENVIRONMENT=ci\n",
        encoding="utf-8",
    )

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.langfuse.environment == "dev"


def test_process_langfuse_base_url_beats_dotenv_base_url(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text("LANGFUSE_BASE_URL=https://dotenv.example\n", encoding="utf-8")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://process.example")

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.langfuse.base_url == "https://process.example"


def test_process_alias_beats_dotenv_primary_for_generic_aliases(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "CC_LANGGRAPH_STORAGE_DIR=.storage-dotenv",
                "SKILLS_PATHS=dotenv-skills",
                "PLUGIN_PATHS=dotenv-plugins",
                'MCP_CONFIG_JSON={"servers":{"dotenv":{"enabled":false}}}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("langgraph_agent_blueprint_STORAGE_DIR", ".storage-process")
    monkeypatch.setenv("LG_AGENT_SKILLS_PATHS", "process-skills")
    monkeypatch.setenv("LG_AGENT_PLUGIN_PATHS", "process-plugins")
    monkeypatch.setenv("LG_AGENT_MCP_CONFIG_JSON", '{"servers":{"process":{"enabled":true}}}')

    config = AppConfig.from_env(project_root=tmp_path)

    assert str(config.storage_dir) == ".storage-process"
    assert [path.as_posix() for path in config.skills_paths] == ["process-skills"]
    assert [path.as_posix() for path in config.plugin_paths] == ["process-plugins"]
    assert "process" in config.mcp_config["servers"]


def test_dotenv_loading_does_not_mutate_process_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    (tmp_path / ".env").write_text("LANGFUSE_PUBLIC_KEY=pk-from-dotenv\n", encoding="utf-8")

    config = AppConfig.from_env(project_root=tmp_path)

    assert config.langfuse.public_key == "pk-from-dotenv"
    assert "LANGFUSE_PUBLIC_KEY" not in __import__("os").environ


def test_app_config_redacts_nested_langfuse_secrets(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")

    config = AppConfig.from_env(project_root=tmp_path)
    redacted = config.redacted()

    assert redacted["langfuse"]["public_key"] == "***"
    assert redacted["langfuse"]["secret_key"] == "***"
    assert "sk-lf-test" not in str(redacted)
