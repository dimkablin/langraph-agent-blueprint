"""Typed runtime configuration loaded from environment, CLI overrides, and project settings."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models.observability import LangfuseConfig


PermissionMode = Literal["default", "accept_edits", "bypass_read_only", "plan", "strict"]
ProviderName = Literal["anthropic", "openai", "ollama", "openai_compatible", "fake"]


class AppConfig(BaseModel):
    """Typed runtime configuration loaded from env, CLI, project, and tests."""

    llm_provider: ProviderName = Field(default="fake")
    model_name: str = Field(default="fake-model")
    storage_dir: Path = Field(default_factory=lambda: Path(".storage"))
    project_root: Path | None = None
    cwd: Path | None = None
    permission_mode: PermissionMode = "default"
    network_enabled: bool = False
    shell_timeout_seconds: float = 30.0
    tool_output_limit: int = 12000
    auto_compact_threshold: int = 12000
    max_recent_messages_after_compact: int = 6
    skills_paths: list[Path] = Field(default_factory=list)
    plugin_paths: list[Path] = Field(default_factory=list)
    mcp_config: dict[str, Any] = Field(default_factory=dict)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ]
    )

    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str | None = None

    @classmethod
    def from_env(cls, **overrides: Any) -> "AppConfig":
        """Build config from environment variables with explicit overrides winning."""

        dotenv = _load_dotenv_values(Path(overrides.get("project_root") or Path.cwd()) / ".env")

        environ = os.environ

        def env_value(key: str, default: str | None = None) -> str | None:
            return layered_get(key, dotenv_values=dotenv, environ=environ, default=default)

        storage_dir = layered_get("CC_LANGGRAPH_STORAGE_DIR", "langgraph_agent_blueprint_STORAGE_DIR", dotenv_values=dotenv, environ=environ)
        provider = env_value("LLM_PROVIDER", "fake")
        model_name = layered_get("MODEL_NAME", "OLLAMA_MODEL", dotenv_values=dotenv, environ=environ, default="fake-model")
        langfuse_enabled = cls._bool(env_value("LANGFUSE_ENABLED"), default=False)
        langfuse_base_url = layered_get("LANGFUSE_BASE_URL", "LANGFUSE_HOST", dotenv_values=dotenv, environ=environ)
        langfuse_environment = layered_get(
            "LANGFUSE_ENVIRONMENT",
            "LANGFUSE_TRACING_ENVIRONMENT",
            dotenv_values=dotenv,
            environ=environ,
            default="dev",
        )
        values: dict[str, Any] = {
            "llm_provider": provider,
            "model_name": model_name,
            "storage_dir": Path(storage_dir) if storage_dir else Path(".storage"),
            "permission_mode": env_value("PERMISSION_MODE", "default"),
            "network_enabled": str(env_value("NETWORK_ENABLED", "false")).lower() in {"1", "true", "yes"},
            "anthropic_api_key": env_value("ANTHROPIC_API_KEY"),
            "anthropic_model": env_value("ANTHROPIC_MODEL"),
            "openai_api_key": env_value("OPENAI_API_KEY"),
            "openai_model": env_value("OPENAI_MODEL"),
            "ollama_base_url": env_value("OLLAMA_BASE_URL", "http://localhost:11434"),
            "ollama_model": env_value("OLLAMA_MODEL", "llama3.1"),
            "openai_compatible_base_url": env_value("OPENAI_COMPATIBLE_BASE_URL"),
            "openai_compatible_api_key": env_value("OPENAI_COMPATIBLE_API_KEY"),
            "openai_compatible_model": env_value("OPENAI_COMPATIBLE_MODEL"),
            "skills_paths": [
                Path(item)
                for item in cls._split_path_list(layered_get("SKILLS_PATHS", "LG_AGENT_SKILLS_PATHS", dotenv_values=dotenv, environ=environ))
            ],
            "plugin_paths": [
                Path(item)
                for item in cls._split_path_list(layered_get("PLUGIN_PATHS", "LG_AGENT_PLUGIN_PATHS", dotenv_values=dotenv, environ=environ))
            ],
            "mcp_config": cls._json_config(layered_get("MCP_CONFIG_JSON", "LG_AGENT_MCP_CONFIG_JSON", dotenv_values=dotenv, environ=environ)),
            "langfuse": LangfuseConfig(
                enabled=langfuse_enabled,
                public_key=env_value("LANGFUSE_PUBLIC_KEY"),
                secret_key=env_value("LANGFUSE_SECRET_KEY"),
                base_url=langfuse_base_url,
                environment=langfuse_environment,
                release=env_value("LANGFUSE_RELEASE"),
                trace_user_id=env_value("LANGFUSE_TRACE_USER_ID"),
                debug=cls._bool(env_value("LANGFUSE_DEBUG"), default=False),
                capture_inputs=cls._bool(env_value("LANGFUSE_CAPTURE_INPUTS"), default=True),
                capture_outputs=cls._bool(env_value("LANGFUSE_CAPTURE_OUTPUTS"), default=True),
                include_project_paths=cls._bool(env_value("LANGFUSE_INCLUDE_PROJECT_PATHS"), default=False),
                runtime_events_mode=env_value("LANGFUSE_RUNTIME_EVENTS_MODE", "high_signal"),
            ),
            "cors_allowed_origins": cls._split_csv(
                env_value("CORS_ALLOWED_ORIGINS"),
                [
                    "http://127.0.0.1:5173",
                    "http://localhost:5173",
                    "http://127.0.0.1:4173",
                    "http://localhost:4173",
                ],
            ),
        }
        values.update(overrides)
        return cls(**values)

    @staticmethod
    def _split_csv(value: str | None, default: list[str]) -> list[str]:
        if not value:
            return default
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _split_path_list(value: str | None) -> list[str]:
        if not value:
            return []
        separators = [os.pathsep, ","]
        items = [value]
        for separator in separators:
            items = [part for item in items for part in item.split(separator)]
        return [item.strip() for item in items if item.strip()]

    @staticmethod
    def _bool(value: str | None, *, default: bool = False) -> bool:
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _json_config(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def effective_model(self) -> str:
        """Return the model name for the selected provider."""

        if self.llm_provider == "ollama":
            return self.ollama_model
        if self.llm_provider == "openai" and self.openai_model:
            return self.openai_model
        if self.llm_provider == "anthropic" and self.anthropic_model:
            return self.anthropic_model
        if self.llm_provider == "openai_compatible" and self.openai_compatible_model:
            return self.openai_compatible_model
        return self.model_name

    def redacted(self) -> dict[str, Any]:
        """Return config suitable for events/logs without secrets."""

        data = self.model_dump(mode="json")
        return _redact_for_display(data)


def _redact_for_display(value: Any, key: str | None = None) -> Any:
    """Recursively redact secrets from config/status dictionaries."""

    sensitive_parts = ("api_key", "apikey", "authorization", "auth", "key", "password", "secret", "token")
    if key and any(part in key.lower() for part in sensitive_parts):
        return "***" if value not in (None, "") else None
    if isinstance(value, dict):
        return {str(item_key): _redact_for_display(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_for_display(item) for item in value]
    return value


def layered_get(
    primary: str,
    alias: str | None = None,
    *,
    dotenv_values: Mapping[str, str],
    environ: Mapping[str, str],
    default: str | None = None,
) -> str | None:
    """Read config with process env above dotenv and primary above alias per layer."""

    if primary in environ:
        return environ[primary]
    if alias and alias in environ:
        return environ[alias]
    if primary in dotenv_values:
        return dotenv_values[primary]
    if alias and alias in dotenv_values:
        return dotenv_values[alias]
    return default


def _load_dotenv_values(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE pairs from a project .env file without mutating process env."""

    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key.startswith("#"):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values
