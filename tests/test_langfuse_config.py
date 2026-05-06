"""Langfuse config loading and redaction coverage."""

from __future__ import annotations

from langgraph_agent_blueprint.config import AppConfig


def test_langfuse_env_loading_prefers_base_url_over_host(monkeypatch) -> None:
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

    config = AppConfig.from_env()

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


def test_langfuse_tracing_environment_alias(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "ci")

    config = AppConfig.from_env()

    assert config.langfuse.environment == "ci"


def test_app_config_redacts_nested_langfuse_secrets(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")

    config = AppConfig.from_env()
    redacted = config.redacted()

    assert redacted["langfuse"]["public_key"] == "***"
    assert redacted["langfuse"]["secret_key"] == "***"
    assert "sk-lf-test" not in str(redacted)
