"""Typed runtime configuration loaded from environment, CLI overrides, and project settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


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

        storage_dir = os.getenv("CC_LANGGRAPH_STORAGE_DIR") or os.getenv("CLAUDE_CODE_LANGGRAPH_STORAGE_DIR")
        provider = os.getenv("LLM_PROVIDER", "fake")
        model_name = os.getenv("MODEL_NAME") or os.getenv("OLLAMA_MODEL") or "fake-model"
        values: dict[str, Any] = {
            "llm_provider": provider,
            "model_name": model_name,
            "storage_dir": Path(storage_dir) if storage_dir else Path(".storage"),
            "permission_mode": os.getenv("PERMISSION_MODE", "default"),
            "network_enabled": os.getenv("NETWORK_ENABLED", "false").lower() in {"1", "true", "yes"},
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
            "anthropic_model": os.getenv("ANTHROPIC_MODEL"),
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "openai_model": os.getenv("OPENAI_MODEL"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.1"),
            "openai_compatible_base_url": os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
            "openai_compatible_api_key": os.getenv("OPENAI_COMPATIBLE_API_KEY"),
            "openai_compatible_model": os.getenv("OPENAI_COMPATIBLE_MODEL"),
            "cors_allowed_origins": cls._split_csv(
                os.getenv("CORS_ALLOWED_ORIGINS"),
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
        for key in list(data):
            if "key" in key.lower() or "token" in key.lower():
                data[key] = "***" if data[key] else None
        return data
