"""Runtime behavior tests for selected workspace roots."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models import AgentRunInput
from langgraph_agent_blueprint.services.tool_execution_service import ToolExecutionService
from langgraph_agent_blueprint.tools.shell_tools import BashTool

from .helpers import AllowAllPermissions, ScriptedChatModel, ai_final, ai_tool_call, expect_tool_result


def test_runtime_project_id_uses_selected_workspace_for_file_tools(tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    app_root.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (app_root / "README.md").write_text("wrong root", encoding="utf-8")
    (workspace_root / "README.md").write_text("selected root", encoding="utf-8")
    runtime, project_id = _runtime_with_workspace(tmp_path, app_root, workspace_root)
    model = ScriptedChatModel(
        [
            ai_tool_call("read_file", {"path": "README.md"}, call_id="read_selected"),
            expect_tool_result("read_selected", contains="selected root"),
            ai_final("done"),
        ]
    )
    runtime.dependencies.model_provider = model

    result = runtime.run(AgentRunInput(message="Read README.", project_id=project_id))

    assert result.status == "success"
    model.assert_no_unused_steps()


def test_runtime_project_id_uses_selected_workspace_for_shell_cwd(tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    app_root.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    runtime, project_id = _runtime_with_workspace(tmp_path, app_root, workspace_root)
    model = ScriptedChatModel(
        [
            ai_tool_call("bash", {"command": "python -c \"import os; print(os.getcwd())\""}, call_id="pwd"),
            expect_tool_result("pwd", contains=workspace_root.name),
            ai_final("done"),
        ]
    )
    runtime.dependencies.model_provider = model

    result = runtime.run(AgentRunInput(message="Show cwd.", project_id=project_id))

    assert result.status == "success"
    model.assert_no_unused_steps()


def test_changed_files_are_relative_to_selected_workspace(tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    app_root.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    runtime, project_id = _runtime_with_workspace(tmp_path, app_root, workspace_root)
    model = ScriptedChatModel(
        [
            ai_tool_call("write_file", {"path": "src/new.py", "content": "print('ok')\n"}, call_id="write_new"),
            expect_tool_result("write_new", contains="Wrote"),
            ai_final("done"),
        ]
    )
    runtime.dependencies.model_provider = model

    result = runtime.run(AgentRunInput(message="Create file.", project_id=project_id))

    assert result.changed_files == ["src/new.py"]
    assert (workspace_root / "src" / "new.py").read_text(encoding="utf-8") == "print('ok')\n"
    assert not (app_root / "src" / "new.py").exists()


def _runtime_with_workspace(tmp_path: Path, app_root: Path, workspace_root: Path) -> tuple[AssistantGraphRuntime, str]:
    config = AppConfig(
        storage_dir=tmp_path / "storage",
        project_root=app_root,
        cwd=app_root,
        llm_provider="fake",
    )
    deps = build_dependencies(config)
    deps.permission_service = AllowAllPermissions()
    workspace = deps.workspace_service.add_workspace(workspace_root)
    deps.workspace_service.select_workspace(workspace.project_id)
    deps.tool_registry.register(BashTool(deps.tool_registry.get("bash").shell_service))
    deps.tool_execution_service = ToolExecutionService(deps.tool_registry, config.tool_output_limit, deps.session_storage)
    runtime = AssistantGraphRuntime(deps)
    return runtime, workspace.project_id
