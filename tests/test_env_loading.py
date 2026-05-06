"""Tests for loading runtime configuration from a project .env file."""

from __future__ import annotations

from claude_code_langgraph.config import AppConfig


def test_from_env_loads_project_dotenv_when_process_env_is_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "LLM_PROVIDER=openai_compatible",
                "OPENAI_COMPATIBLE_BASE_URL=http://localhost:11434/v1",
                "OPENAI_COMPATIBLE_MODEL=qwen3:14b",
                "OPENAI_COMPATIBLE_API_KEY=not-needed",
            ]
        ),
        encoding="utf-8",
    )

    config = AppConfig.from_env()

    assert config.llm_provider == "openai_compatible"
    assert config.openai_compatible_base_url == "http://localhost:11434/v1"
    assert config.openai_compatible_model == "qwen3:14b"
    assert config.openai_compatible_api_key == "not-needed"


def test_process_env_overrides_project_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    (tmp_path / ".env").write_text("LLM_PROVIDER=openai_compatible\n", encoding="utf-8")

    config = AppConfig.from_env()

    assert config.llm_provider == "fake"
