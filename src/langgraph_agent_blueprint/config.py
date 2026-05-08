"""Typed runtime configuration loaded from environment, CLI overrides, and project settings."""

from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from langgraph_agent_blueprint.models.config import ConfigDiagnostic, ConfigSource, ConfigValueOrigin, EffectiveConfigReport
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
    web_fetch_allow_private_hosts: bool = False
    web_fetch_max_bytes: int = 1_000_000
    context_max_tokens: int = 8000
    context_max_file_bytes: int = 200_000
    context_max_directory_files: int = 200
    context_max_glob_files: int = 100
    shell_timeout_seconds: float = 30.0
    tool_output_limit: int = 12000
    auto_compact_threshold: int = 12000
    max_recent_messages_after_compact: int = 6
    skills_paths: list[Path] = Field(default_factory=list)
    plugin_paths: list[Path] = Field(default_factory=list)
    plugin_git_timeout_seconds: float = 60.0
    mcp_config: dict[str, Any] = Field(default_factory=dict)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    config_report: EffectiveConfigReport | None = None
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

        config, _report = cls.load_with_report(**overrides)
        return config

    @classmethod
    def load_with_report(cls, **overrides: Any) -> tuple["AppConfig", EffectiveConfigReport]:
        """Build config plus a redacted source/value explanation report."""

        special_keys = {"environ", "user_config_path", "project_config_path"}
        environ = dict(overrides.pop("environ", os.environ))
        project_root = Path(overrides.get("project_root") or Path.cwd())
        dotenv_path = project_root / ".env"
        user_config_path = Path(overrides.pop("user_config_path", _default_user_config_path()))
        project_config_path = Path(overrides.pop("project_config_path", _default_project_config_path(project_root)))
        for key in list(overrides):
            if key in special_keys:
                overrides.pop(key, None)

        sources: list[ConfigSource] = []
        diagnostics: list[ConfigDiagnostic] = []
        values: dict[str, Any] = {}
        origins: dict[str, str] = {}

        defaults = _defaults_for_report(cls)
        _merge_layer(values, origins, defaults, "defaults")
        sources.append(ConfigSource(name="defaults", kind="defaults", loaded=True))

        dotenv = _load_dotenv_values(dotenv_path)
        sources.append(ConfigSource(name=".env", kind="dotenv", path=str(dotenv_path), loaded=dotenv_path.exists()))
        _merge_layer(values, origins, _normalize_env_layer(dotenv, "dotenv", diagnostics), "dotenv")

        user_data, user_error = _load_toml_values(user_config_path)
        sources.append(ConfigSource(name="user_config", kind="user_config", path=str(user_config_path), loaded=user_error is None and user_config_path.exists(), error=user_error))
        if user_error:
            diagnostics.append(ConfigDiagnostic(key="user_config", status="warning", message=user_error, source="user_config"))
        _merge_layer(values, origins, _normalize_toml_layer(user_data, "user_config", diagnostics), "user_config")

        project_data, project_error = _load_toml_values(project_config_path)
        sources.append(
            ConfigSource(
                name="project_config",
                kind="project_config",
                path=str(project_config_path),
                loaded=project_error is None and project_config_path.exists(),
                error=project_error,
            )
        )
        if project_error:
            diagnostics.append(ConfigDiagnostic(key="project_config", status="warning", message=project_error, source="project_config"))
        _merge_layer(values, origins, _normalize_toml_layer(project_data, "project_config", diagnostics), "project_config")

        _merge_layer(values, origins, _normalize_env_layer(environ, "env", diagnostics), "env")
        sources.append(ConfigSource(name="process_env", kind="env", loaded=True))

        override_values = {key: value for key, value in overrides.items() if value is not None}
        _merge_layer(values, origins, override_values, "override")
        if override_values:
            sources.append(ConfigSource(name="overrides", kind="override", loaded=True))

        config_values = _coerce_final_values(values, origins, diagnostics)
        try:
            config = cls(**config_values)
        except ValidationError as exc:
            diagnostics.append(ConfigDiagnostic(key="config", status="error", message=str(exc), source=None))
            fallback = _defaults_for_report(cls)
            fallback.update({key: value for key, value in config_values.items() if key in cls.model_fields and key != "config_report"})
            config = cls.model_validate(fallback)
        report = EffectiveConfigReport(
            sources=sources,
            values=_value_origins(config, origins),
            diagnostics=diagnostics or [ConfigDiagnostic(key="config", status="ok", message="Config loaded successfully")],
        )
        return config.model_copy(update={"config_report": report}), report

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
    def _int(value: str | None, *, default: int) -> int:
        if value is None:
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _float(value: str | None, *, default: float) -> float:
        if value is None:
            return default
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

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

        data = self.model_dump(mode="json", exclude={"config_report"})
        return _redact_for_display(data)


def format_config_show(config: AppConfig) -> str:
    """Render redacted effective config for human-facing commands."""

    lines = ["Config:"]
    for key, value in sorted(config.redacted().items()):
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def format_config_explain(report: EffectiveConfigReport | None) -> str:
    """Render config source/value origins without exposing secrets."""

    if report is None:
        return "Config explain data is unavailable."
    lines = ["Sources:"]
    for source in report.sources:
        status = "loaded" if source.loaded else "not loaded"
        detail = f" ({source.path})" if source.path else ""
        error = f" error: {source.error}" if source.error else ""
        lines.append(f"- {source.name} [{source.kind}]: {status}{detail}{error}")
    lines.append("Values:")
    for value in sorted(report.values, key=lambda item: item.key):
        suffix = " (redacted)" if value.redacted else ""
        lines.append(f"- {value.key}: {value.value_repr} [{value.source}]{suffix}")
    return "\n".join(lines)


def format_config_validate(report: EffectiveConfigReport | None) -> str:
    """Render config diagnostics for human-facing commands."""

    if report is None:
        return "Config diagnostics: unavailable"
    lines = ["Config diagnostics:"]
    for diagnostic in report.diagnostics:
        source = f" [{diagnostic.source}]" if diagnostic.source else ""
        lines.append(f"- {diagnostic.status}: {diagnostic.key}{source}: {diagnostic.message}")
    return "\n".join(lines)


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


def _default_user_config_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "langgraph-agent-blueprint" / "config.toml"
    return Path.home() / ".config" / "langgraph-agent-blueprint" / "config.toml"


def _default_project_config_path(project_root: Path) -> Path:
    local = project_root / ".lg-agent" / "config.toml"
    if local.exists():
        return local
    return project_root / "langgraph-agent.toml"


def _defaults_for_report(cls: type[AppConfig]) -> dict[str, Any]:
    config = cls()
    data = config.model_dump(mode="python", exclude={"config_report"})
    return data


def _load_toml_values(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), None
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return {}, str(exc)


def _merge_layer(values: dict[str, Any], origins: dict[str, str], layer: dict[str, Any], source: str) -> None:
    for key, value in layer.items():
        if key == "langfuse" and isinstance(value, dict):
            existing = values.get("langfuse")
            if isinstance(existing, LangfuseConfig):
                existing_data = existing.model_dump(mode="python")
            elif isinstance(existing, dict):
                existing_data = dict(existing)
            else:
                existing_data = {}
            existing_data.update(value)
            values[key] = existing_data
        elif key == "mcp_config" and isinstance(value, dict):
            existing = values.get("mcp_config") if isinstance(values.get("mcp_config"), dict) else {}
            values[key] = _deep_merge_dicts(dict(existing), value)
        else:
            values[key] = value
        origins[key] = source


def _deep_merge_dicts(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _normalize_env_layer(raw: Mapping[str, Any], source: str, diagnostics: list[ConfigDiagnostic]) -> dict[str, Any]:
    def first(*names: str) -> Any:
        for name in names:
            if name in raw:
                return raw[name]
            upper_name = name.upper()
            if upper_name in raw:
                return raw[upper_name]
        return None

    values: dict[str, Any] = {}
    _set_if_present(values, "llm_provider", first("LLM_PROVIDER"))
    _set_if_present(values, "model_name", first("MODEL_NAME", "OLLAMA_MODEL"))
    _set_if_present(values, "storage_dir", first("CC_LANGGRAPH_STORAGE_DIR", "langgraph_agent_blueprint_STORAGE_DIR"))
    _set_if_present(values, "permission_mode", first("PERMISSION_MODE"))
    _set_if_present(values, "network_enabled", _parse_bool(first("NETWORK_ENABLED"), "network_enabled", source, diagnostics))
    _set_if_present(values, "web_fetch_allow_private_hosts", _parse_bool(first("WEB_FETCH_ALLOW_PRIVATE_HOSTS"), "web_fetch_allow_private_hosts", source, diagnostics))
    _set_if_present(values, "web_fetch_max_bytes", _parse_int(first("WEB_FETCH_MAX_BYTES"), "web_fetch_max_bytes", source, diagnostics))
    _set_if_present(values, "context_max_tokens", _parse_int(first("CONTEXT_MAX_TOKENS"), "context_max_tokens", source, diagnostics))
    _set_if_present(values, "context_max_file_bytes", _parse_int(first("CONTEXT_MAX_FILE_BYTES"), "context_max_file_bytes", source, diagnostics))
    _set_if_present(values, "context_max_directory_files", _parse_int(first("CONTEXT_MAX_DIRECTORY_FILES"), "context_max_directory_files", source, diagnostics))
    _set_if_present(values, "context_max_glob_files", _parse_int(first("CONTEXT_MAX_GLOB_FILES"), "context_max_glob_files", source, diagnostics))
    _set_if_present(values, "anthropic_api_key", first("ANTHROPIC_API_KEY"))
    _set_if_present(values, "anthropic_model", first("ANTHROPIC_MODEL"))
    _set_if_present(values, "openai_api_key", first("OPENAI_API_KEY"))
    _set_if_present(values, "openai_model", first("OPENAI_MODEL"))
    _set_if_present(values, "ollama_base_url", first("OLLAMA_BASE_URL"))
    _set_if_present(values, "ollama_model", first("OLLAMA_MODEL"))
    _set_if_present(values, "openai_compatible_base_url", first("OPENAI_COMPATIBLE_BASE_URL"))
    _set_if_present(values, "openai_compatible_api_key", first("OPENAI_COMPATIBLE_API_KEY"))
    _set_if_present(values, "openai_compatible_model", first("OPENAI_COMPATIBLE_MODEL"))
    if first("SKILLS_PATHS", "LG_AGENT_SKILLS_PATHS") is not None:
        values["skills_paths"] = [Path(item) for item in AppConfig._split_path_list(str(first("SKILLS_PATHS", "LG_AGENT_SKILLS_PATHS")))]
    if first("PLUGIN_PATHS", "LG_AGENT_PLUGIN_PATHS") is not None:
        values["plugin_paths"] = [Path(item) for item in AppConfig._split_path_list(str(first("PLUGIN_PATHS", "LG_AGENT_PLUGIN_PATHS")))]
    _set_if_present(values, "plugin_git_timeout_seconds", _parse_float(first("PLUGIN_GIT_TIMEOUT_SECONDS"), "plugin_git_timeout_seconds", source, diagnostics))
    if first("MCP_CONFIG_JSON", "LG_AGENT_MCP_CONFIG_JSON") is not None:
        values["mcp_config"] = _parse_json_config(str(first("MCP_CONFIG_JSON", "LG_AGENT_MCP_CONFIG_JSON")), "mcp_config", source, diagnostics)
    if first("CORS_ALLOWED_ORIGINS") is not None:
        values["cors_allowed_origins"] = AppConfig._split_csv(str(first("CORS_ALLOWED_ORIGINS")), [])
    langfuse: dict[str, Any] = {}
    _set_if_present(langfuse, "enabled", _parse_bool(first("LANGFUSE_ENABLED"), "langfuse.enabled", source, diagnostics))
    _set_if_present(langfuse, "public_key", first("LANGFUSE_PUBLIC_KEY"))
    _set_if_present(langfuse, "secret_key", first("LANGFUSE_SECRET_KEY"))
    _set_if_present(langfuse, "base_url", first("LANGFUSE_BASE_URL", "LANGFUSE_HOST"))
    _set_if_present(langfuse, "environment", first("LANGFUSE_ENVIRONMENT", "LANGFUSE_TRACING_ENVIRONMENT"))
    _set_if_present(langfuse, "release", first("LANGFUSE_RELEASE"))
    _set_if_present(langfuse, "trace_user_id", first("LANGFUSE_TRACE_USER_ID"))
    _set_if_present(langfuse, "debug", _parse_bool(first("LANGFUSE_DEBUG"), "langfuse.debug", source, diagnostics))
    _set_if_present(langfuse, "capture_inputs", _parse_bool(first("LANGFUSE_CAPTURE_INPUTS"), "langfuse.capture_inputs", source, diagnostics))
    _set_if_present(langfuse, "capture_outputs", _parse_bool(first("LANGFUSE_CAPTURE_OUTPUTS"), "langfuse.capture_outputs", source, diagnostics))
    _set_if_present(langfuse, "include_project_paths", _parse_bool(first("LANGFUSE_INCLUDE_PROJECT_PATHS"), "langfuse.include_project_paths", source, diagnostics))
    _set_if_present(langfuse, "runtime_events_mode", first("LANGFUSE_RUNTIME_EVENTS_MODE"))
    if langfuse:
        values["langfuse"] = langfuse
    return {key: value for key, value in values.items() if value is not None}


def _normalize_toml_layer(raw: dict[str, Any], source: str, diagnostics: list[ConfigDiagnostic]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    direct_keys = {
        "llm_provider",
        "model_name",
        "storage_dir",
        "permission_mode",
        "network_enabled",
        "web_fetch_allow_private_hosts",
        "web_fetch_max_bytes",
        "context_max_tokens",
        "context_max_file_bytes",
        "context_max_directory_files",
        "context_max_glob_files",
        "shell_timeout_seconds",
        "tool_output_limit",
        "auto_compact_threshold",
        "max_recent_messages_after_compact",
        "skills_paths",
        "plugin_paths",
        "plugin_git_timeout_seconds",
        "anthropic_api_key",
        "anthropic_model",
        "openai_api_key",
        "openai_model",
        "ollama_base_url",
        "ollama_model",
        "openai_compatible_base_url",
        "openai_compatible_api_key",
        "openai_compatible_model",
        "cors_allowed_origins",
    }
    for key in direct_keys:
        if key in raw:
            values[key] = raw[key]
    if isinstance(raw.get("web_fetch"), dict):
        web = raw["web_fetch"]
        _set_if_present(values, "web_fetch_allow_private_hosts", web.get("allow_private_hosts"))
        _set_if_present(values, "web_fetch_max_bytes", web.get("max_bytes"))
    if isinstance(raw.get("context"), dict):
        context = raw["context"]
        _set_if_present(values, "context_max_tokens", context.get("max_tokens"))
        _set_if_present(values, "context_max_file_bytes", context.get("max_file_bytes"))
        _set_if_present(values, "context_max_directory_files", context.get("max_directory_files"))
        _set_if_present(values, "context_max_glob_files", context.get("max_glob_files"))
    if isinstance(raw.get("plugins"), dict):
        plugins = raw["plugins"]
        _set_if_present(values, "plugin_paths", plugins.get("paths"))
        _set_if_present(values, "plugin_git_timeout_seconds", plugins.get("git_timeout_seconds"))
    if isinstance(raw.get("skills"), dict):
        _set_if_present(values, "skills_paths", raw["skills"].get("paths"))
    if isinstance(raw.get("langfuse"), dict):
        values["langfuse"] = dict(raw["langfuse"])
    if isinstance(raw.get("observability"), dict) and isinstance(raw["observability"].get("langfuse"), dict):
        values["langfuse"] = {**dict(values.get("langfuse") or {}), **dict(raw["observability"]["langfuse"])}
    if isinstance(raw.get("mcp"), dict):
        values["mcp_config"] = dict(raw["mcp"])
    return _validate_toml_value_types(values, source, diagnostics)


def _validate_toml_value_types(values: dict[str, Any], source: str, diagnostics: list[ConfigDiagnostic]) -> dict[str, Any]:
    bool_keys = {"network_enabled", "web_fetch_allow_private_hosts"}
    int_keys = {"web_fetch_max_bytes", "context_max_tokens", "context_max_file_bytes", "context_max_directory_files", "context_max_glob_files"}
    float_keys = {"plugin_git_timeout_seconds", "shell_timeout_seconds"}
    path_list_keys = {"skills_paths", "plugin_paths"}
    clean: dict[str, Any] = {}
    for key, value in values.items():
        if key in bool_keys and not isinstance(value, bool):
            diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Expected boolean, got {type(value).__name__}", source=source))
            continue
        if key in int_keys and not isinstance(value, int):
            diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Expected integer, got {type(value).__name__}", source=source))
            continue
        if key in float_keys and not isinstance(value, (int, float)):
            diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Expected number, got {type(value).__name__}", source=source))
            continue
        if key in path_list_keys and isinstance(value, str):
            clean[key] = [Path(value)]
            continue
        if key in path_list_keys and isinstance(value, list):
            clean[key] = [Path(str(item)) for item in value]
            continue
        clean[key] = value
    return clean


def _coerce_final_values(values: dict[str, Any], origins: dict[str, str], diagnostics: list[ConfigDiagnostic]) -> dict[str, Any]:
    coerced = dict(values)
    for key in ["storage_dir", "project_root", "cwd"]:
        if coerced.get(key) is not None:
            coerced[key] = Path(coerced[key])
    for key in ["skills_paths", "plugin_paths"]:
        if coerced.get(key) is not None:
            coerced[key] = [Path(item) for item in coerced[key]]
    if isinstance(coerced.get("langfuse"), dict):
        try:
            coerced["langfuse"] = LangfuseConfig.model_validate(coerced["langfuse"])
        except ValidationError as exc:
            diagnostics.append(ConfigDiagnostic(key="langfuse", status="error", message=str(exc), source=origins.get("langfuse")))
            coerced["langfuse"] = LangfuseConfig()
    return {key: value for key, value in coerced.items() if key in AppConfig.model_fields and key != "config_report"}


def _value_origins(config: AppConfig, origins: dict[str, str]) -> list[ConfigValueOrigin]:
    data = config.model_dump(mode="json", exclude={"config_report"})
    values = []
    for key, value in sorted(data.items()):
        redacted = _redact_for_display(value, key) != value
        values.append(
            ConfigValueOrigin(
                key=key,
                value_repr=str(_redact_for_display(value, key)),
                source=origins.get(key, "defaults"),
                redacted=redacted,
            )
        )
    return values


def _set_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def _parse_bool(value: Any, key: str, source: str, diagnostics: list[ConfigDiagnostic]) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Invalid boolean value: {value}", source=source))
    return None


def _parse_int(value: Any, key: str, source: str, diagnostics: list[ConfigDiagnostic]) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Invalid integer value: {value}", source=source))
        return None
    if parsed <= 0:
        diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Expected positive integer, got {value}", source=source))
        return None
    return parsed


def _parse_float(value: Any, key: str, source: str, diagnostics: list[ConfigDiagnostic]) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Invalid number value: {value}", source=source))
        return None
    if parsed <= 0:
        diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=f"Expected positive number, got {value}", source=source))
        return None
    return parsed


def _parse_json_config(value: str, key: str, source: str, diagnostics: list[ConfigDiagnostic]) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        diagnostics.append(ConfigDiagnostic(key=key, status="warning", message=str(exc), source=source))
        return {}
    if not isinstance(parsed, dict):
        diagnostics.append(ConfigDiagnostic(key=key, status="warning", message="Expected JSON object", source=source))
        return {}
    return parsed


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
