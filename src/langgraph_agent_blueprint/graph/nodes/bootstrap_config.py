"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models import AgentActivityEvent, AgentActivityRef, AgentActivitySource, event
from langgraph_agent_blueprint.utils.activity import safe_activity_data


def bootstrap_config_node(state: dict, deps: AppDependencies) -> dict:
    """Seed config-derived metadata, workspace paths, and permission mode at graph start."""

    config = deps.config
    metadata = dict(state.get("metadata", {}))
    metadata.setdefault("config", config.redacted())
    if config.config_report is not None:
        metadata.setdefault("config_report", config.config_report.model_dump(mode="json"))
    metadata.setdefault("model_name", config.effective_model())
    metadata.setdefault("input_normalized", False)
    permissions = {"mode": config.permission_mode, **state.get("permissions", {})}
    project_root = state.get("project_root") or str((config.project_root or ".").resolve())
    workspace = state.get("workspace") if isinstance(state.get("workspace"), dict) else {}
    events = [
        event(
            "session_started",
            session_id=state.get("session_id"),
            project_root=state.get("project_root"),
            activity=_runtime_activity(
                "runtime.run.started",
                title="Run started",
                status="running",
                data={"session_id": state.get("session_id"), "project_id": state.get("project_id")},
            ).model_dump(mode="json"),
        ),
        event(
            "agent_activity",
            activity=_workspace_activity(workspace, project_root).model_dump(mode="json"),
        ),
    ]
    if workspace.get("is_git_repo"):
        events.append(event("agent_activity", activity=_git_activity(workspace).model_dump(mode="json")))
    return {
        "project_root": project_root,
        "cwd": state.get("cwd") or str((config.cwd or config.project_root or ".").resolve()),
        "permissions": permissions,
        "metadata": metadata,
        "ui_events": events,
    }


def _runtime_activity(activity_type: str, *, title: str, status: str, data: dict) -> AgentActivityEvent:
    return AgentActivityEvent(
        type=activity_type,
        source=AgentActivitySource(kind="runtime", component="AssistantGraphRuntime"),
        category="runtime",
        status=status,  # type: ignore[arg-type]
        title=title,
        data=safe_activity_data(data),
    )


def _workspace_activity(workspace: dict, project_root: str) -> AgentActivityEvent:
    path = workspace.get("root_path") or project_root
    display_name = workspace.get("display_name") or path
    return AgentActivityEvent(
        type="workspace.selected",
        source=AgentActivitySource(kind="workspace", name=str(display_name), component="WorkspaceService"),
        category="workspace",
        status="success",
        title="Workspace selected",
        summary=str(display_name),
        data=safe_activity_data(
            {
                "project_id": workspace.get("project_id"),
                "display_name": display_name,
                "root_path": path,
            }
        ),
        refs=[AgentActivityRef(kind="workspace", path=str(path), id=workspace.get("project_id"))],
    )


def _git_activity(workspace: dict) -> AgentActivityEvent:
    return AgentActivityEvent(
        type="git.context.loaded",
        source=AgentActivitySource(kind="git", component="WorkspaceService"),
        category="git",
        status="success",
        title="Git context loaded",
        summary=f"Branch {workspace.get('current_branch') or 'unknown'}; dirty={bool(workspace.get('dirty'))}.",
        data=safe_activity_data(
            {
                "current_branch": workspace.get("current_branch"),
                "dirty": bool(workspace.get("dirty")),
                "git_status": workspace.get("git_status"),
            }
        ),
    )

