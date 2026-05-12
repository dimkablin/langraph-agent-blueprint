"""P0 behavior-suite fixtures that invoke the public runtime path."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.services.tool_execution_service import ToolExecutionService
from langgraph_agent_blueprint.tools.shell_tools import BashTool, PowerShellTool

from .helpers import (
    AllowAllPermissions,
    DenyRule,
    DenyingPermissions,
    PlanModePermissions,
    RecordingShellExecutor,
    ScriptedChatModel,
    ScriptedStep,
)


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    return project


@pytest.fixture
def scripted_chat_model() -> Any:
    def factory(*, steps: list[ScriptedStep]) -> ScriptedChatModel:
        return ScriptedChatModel(steps)

    return factory


@pytest.fixture
def approving_permissions() -> AllowAllPermissions:
    return AllowAllPermissions()


@pytest.fixture
def denying_permissions() -> DenyingPermissions:
    return DenyingPermissions()


@pytest.fixture
def plan_mode_permissions() -> PlanModePermissions:
    return PlanModePermissions()


@pytest.fixture
def runtime_factory() -> Any:
    def factory(
        *,
        project_root: Path,
        chat_model: ScriptedChatModel,
        permissions: Any,
        shell_executor: Any | None = None,
        config_overrides: dict[str, Any] | None = None,
    ) -> AssistantGraphRuntime:
        overrides = dict(config_overrides or {})
        config = AppConfig(
            storage_dir=project_root / ".storage",
            project_root=project_root,
            cwd=project_root,
            llm_provider="fake",
            **overrides,
        )
        deps = build_dependencies(config)
        deps.model_provider = chat_model
        deps.permission_service = permissions
        shell = shell_executor or RecordingShellExecutor()
        deps.tool_registry.register(BashTool(shell))
        deps.tool_registry.register(PowerShellTool(shell))
        deps.tool_execution_service = ToolExecutionService(deps.tool_registry, config.tool_output_limit, deps.session_storage)
        return AssistantGraphRuntime(deps)

    return factory


@pytest.fixture
def protected_file_denier() -> DenyingPermissions:
    return DenyingPermissions(
        [
            DenyRule(
                action="edit",
                path=".env",
                reason="Permission denied: protected file edits require explicit approval.",
            )
        ]
    )


@pytest.fixture
def dangerous_shell_denier() -> DenyingPermissions:
    return DenyingPermissions(
        [
            DenyRule(
                action="shell",
                command_contains="remove-item",
                reason="Permission denied: destructive shell command blocked.",
            )
        ]
    )
