from __future__ import annotations

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def bootstrap_config_node(state: dict, deps: AppDependencies) -> dict:
    config = deps.config
    metadata = dict(state.get("metadata", {}))
    metadata.setdefault("config", config.redacted())
    metadata.setdefault("model_name", config.effective_model())
    metadata.setdefault("input_normalized", False)
    permissions = {"mode": config.permission_mode, **state.get("permissions", {})}
    return {
        "project_root": state.get("project_root") or str((config.project_root or ".").resolve()),
        "cwd": state.get("cwd") or str((config.cwd or config.project_root or ".").resolve()),
        "permissions": permissions,
        "metadata": metadata,
        "ui_events": [event("session_started", session_id=state.get("session_id"), project_root=state.get("project_root"))],
    }

