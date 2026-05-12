"""FastAPI routes for local workspace selection and safe Git branch awareness."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from langgraph_agent_blueprint.models import GitStatusSummary, WorkspaceCheckoutResult, WorkspaceInfo
from langgraph_agent_blueprint.services.folder_picker_service import FolderPickerUnavailableError
from langgraph_agent_blueprint.services.git_service import GitBranchNotFoundError, GitCheckoutBlockedError, GitServiceError
from langgraph_agent_blueprint.services.workspace_service import WorkspaceNotFoundError, WorkspacePathError

from .schemas import WorkspaceAddRequest, WorkspaceCheckoutRequest, WorkspaceSelectRequest

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceInfo])
def list_workspaces(request: Request) -> list[WorkspaceInfo]:
    return request.app.state.runtime.dependencies.workspace_service.list_workspaces()


@router.post("", response_model=WorkspaceInfo)
def add_workspace(request_body: WorkspaceAddRequest, request: Request) -> WorkspaceInfo:
    try:
        return request.app.state.runtime.dependencies.workspace_service.add_workspace(request_body.root_path)
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pick", response_model=WorkspaceInfo | None)
async def pick_workspace_folder(request: Request) -> WorkspaceInfo | None:
    try:
        root_path = request.app.state.runtime.dependencies.folder_picker_service.select_directory(title="Выберите папку проекта")
        if root_path is None:
            return None
        return request.app.state.runtime.dependencies.workspace_service.add_workspace(root_path)
    except FolderPickerUnavailableError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/active", response_model=WorkspaceInfo | None)
def get_active_workspace(request: Request) -> WorkspaceInfo | None:
    return request.app.state.runtime.dependencies.workspace_service.get_active_workspace()


@router.post("/select", response_model=WorkspaceInfo)
def select_workspace(request_body: WorkspaceSelectRequest, request: Request) -> WorkspaceInfo:
    try:
        return request.app.state.runtime.dependencies.workspace_service.select_workspace(request_body.project_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}", response_model=WorkspaceInfo)
def get_workspace(project_id: str, request: Request) -> WorkspaceInfo:
    try:
        return request.app.state.runtime.dependencies.workspace_service.get_workspace(project_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/git/status", response_model=GitStatusSummary | None)
def get_workspace_git_status(project_id: str, request: Request) -> GitStatusSummary | None:
    workspace = get_workspace(project_id, request)
    return workspace.git_status


@router.get("/{project_id}/branches", response_model=list[str])
def list_workspace_branches(project_id: str, request: Request) -> list[str]:
    return get_workspace(project_id, request).branches


@router.post("/{project_id}/checkout", response_model=WorkspaceCheckoutResult)
def checkout_workspace_branch(project_id: str, request_body: WorkspaceCheckoutRequest, request: Request) -> WorkspaceCheckoutResult:
    try:
        return request.app.state.runtime.dependencies.workspace_service.checkout_branch(
            project_id,
            request_body.branch,
            confirm_dirty=request_body.confirm_dirty,
        )
    except GitCheckoutBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (WorkspaceNotFoundError, GitBranchNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (WorkspacePathError, GitServiceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
