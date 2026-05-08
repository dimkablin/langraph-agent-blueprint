"""Read-only FastAPI routes for runtime status panels."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from langgraph_agent_blueprint.models import ConfigDiagnostic

from .schemas import (
    ConfigExplainDTO,
    ConfigShowDTO,
    ConfigValidateDTO,
    HookStatusDTO,
    ObservabilityStatusDTO,
    PluginStatusDTO,
)

router = APIRouter()


@router.get("/plugins", response_model=PluginStatusDTO)
def get_plugins_status(request: Request) -> PluginStatusDTO:
    """Return plugin discovery status and diagnostics without executing plugin code."""

    runtime = request.app.state.runtime
    raw = runtime.dependencies.plugin_service.discover()
    redacted = runtime.dependencies.observability_service.redact_payload(raw)
    return PluginStatusDTO(
        plugins=_list_of_dicts(redacted.get("plugins")),
        contributions=_list_of_dicts(redacted.get("contributions")),
        errors=_list_of_dicts(redacted.get("errors")),
        warnings=_plugin_warning_rows(redacted),
    )


@router.get("/hooks", response_model=HookStatusDTO)
def get_hooks_status(request: Request) -> HookStatusDTO:
    """Return hook registry metadata for a frontend status panel."""

    runtime = request.app.state.runtime
    payload = runtime.dependencies.observability_service.redact_payload(
        {"hooks": runtime.dependencies.hook_registry.snapshot()}
    )
    return HookStatusDTO(hooks=_list_of_dicts(payload.get("hooks")))


@router.get("/config", response_model=ConfigShowDTO)
def get_config(request: Request) -> ConfigShowDTO:
    """Return redacted effective application configuration."""

    config = request.app.state.runtime.dependencies.config
    return ConfigShowDTO(values=config.redacted())


@router.get("/config/explain", response_model=ConfigExplainDTO)
def explain_config(request: Request) -> ConfigExplainDTO:
    """Return config source and value-origin diagnostics for frontend display."""

    report = request.app.state.runtime.dependencies.config.config_report
    if report is None:
        return ConfigExplainDTO()
    return ConfigExplainDTO(
        sources=report.sources,
        values=report.values,
        diagnostics=report.diagnostics,
    )


@router.get("/config/validate", response_model=ConfigValidateDTO)
def validate_config(request: Request) -> ConfigValidateDTO:
    """Return typed config validation diagnostics."""

    report = request.app.state.runtime.dependencies.config.config_report
    diagnostics = list(report.diagnostics) if report is not None else []
    return ConfigValidateDTO(ok=not _has_error_diagnostic(diagnostics), diagnostics=diagnostics)


@router.get("/observability", response_model=ObservabilityStatusDTO)
def get_observability_status(request: Request) -> ObservabilityStatusDTO:
    """Return redacted observability backend status."""

    runtime = request.app.state.runtime
    payload = runtime.dependencies.observability_service.status()
    if payload.get("last_error"):
        redacted_error = runtime.dependencies.observability_service.redact_payload({"last_error": payload["last_error"]})
        payload = {**payload, "last_error": redacted_error.get("last_error")}
    return ObservabilityStatusDTO.model_validate(payload)


def _plugin_warning_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in (
        "hook_warnings",
        "policy_warnings",
        "command_warnings",
        "tool_warnings",
        "mcp_warnings",
        "context_warnings",
        "sdk_warnings",
    ):
        for item in _list_of_dicts(payload.get(key)):
            rows.append({"source": key, **item})
    return rows


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _has_error_diagnostic(diagnostics: list[ConfigDiagnostic]) -> bool:
    return any(item.status == "error" for item in diagnostics)
