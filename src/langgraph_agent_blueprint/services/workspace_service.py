"""Public workspace registry and selection service."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from langgraph_agent_blueprint.models import WorkspaceCheckoutResult, WorkspaceInfo
from langgraph_agent_blueprint.storage import ConfigStorage
from langgraph_agent_blueprint.storage.paths import project_hash

from .git_service import GitService


class WorkspaceServiceError(RuntimeError):
    """Base workspace service error."""


class WorkspacePathError(WorkspaceServiceError, ValueError):
    """Raised when a workspace root is not a valid local directory."""


class WorkspaceNotFoundError(WorkspaceServiceError, KeyError):
    """Raised when a project id is not registered."""


class WorkspaceService:
    """Registry for validated local project roots and their dynamic Git metadata."""

    def __init__(self, storage_dir: str | Path, *, git_service: GitService | None = None) -> None:
        self.storage = ConfigStorage(Path(storage_dir) / "workspaces.json")
        self.git_service = git_service or GitService()

    def add_workspace(self, root_path: str | Path) -> WorkspaceInfo:
        root = self.validate_root_path(root_path)
        now = _now()
        registry = self._load_registry()
        project_id = self.project_id_for_root(root)
        existing = registry["workspaces"].get(project_id, {})
        record = {
            "project_id": project_id,
            "display_name": root.name or str(root),
            "root_path": str(root),
            "created_at": existing.get("created_at") or now,
            "last_opened_at": now,
        }
        registry["workspaces"][project_id] = record
        registry["active_project_id"] = project_id
        self._save_registry(registry)
        return self._workspace_from_record(record)

    def select_workspace(self, project_id: str) -> WorkspaceInfo:
        registry = self._load_registry()
        record = self._record_for_project(registry, project_id)
        record["last_opened_at"] = _now()
        registry["workspaces"][project_id] = record
        registry["active_project_id"] = project_id
        self._save_registry(registry)
        return self._workspace_from_record(record)

    def list_workspaces(self) -> list[WorkspaceInfo]:
        registry = self._load_registry()
        workspaces = [
            workspace
            for item in registry["workspaces"].values()
            if (workspace := self._safe_workspace_from_record(item)) is not None
        ]
        return sorted(workspaces, key=lambda item: (item.last_opened_at or "", item.display_name), reverse=True)

    def get_workspace(self, project_id: str) -> WorkspaceInfo:
        registry = self._load_registry()
        return self._workspace_from_record(self._record_for_project(registry, project_id))

    def get_active_workspace(self) -> WorkspaceInfo | None:
        registry = self._load_registry()
        project_id = registry.get("active_project_id")
        if not project_id:
            return None
        try:
            return self.get_workspace(str(project_id))
        except (WorkspaceNotFoundError, WorkspacePathError):
            return None

    def checkout_branch(self, project_id: str, branch: str, *, confirm_dirty: bool = False) -> WorkspaceCheckoutResult:
        workspace = self.get_workspace(project_id)
        self.git_service.checkout_existing_branch(workspace.root_path, branch, confirm_dirty=confirm_dirty)
        refreshed = self.select_workspace(project_id)
        return WorkspaceCheckoutResult(ok=True, workspace=refreshed, message=f"Checked out {branch}.")

    def validate_root_path(self, root_path: str | Path) -> Path:
        try:
            root = Path(root_path).expanduser().resolve(strict=True)
        except OSError as exc:
            raise WorkspacePathError(f"Workspace path does not exist: {root_path}") from exc
        if not root.is_dir():
            raise WorkspacePathError(f"Workspace path is not a directory: {root}")
        return root

    @staticmethod
    def project_id_for_root(root_path: str | Path) -> str:
        return f"project_{project_hash(root_path)}"

    def _workspace_from_record(self, record: dict[str, Any]) -> WorkspaceInfo:
        root = self.validate_root_path(record["root_path"])
        is_git_repo = self.git_service.is_git_repo(root)
        git_status = self.git_service.status_summary(root) if is_git_repo else None
        payload = {
            **record,
            "root_path": str(root),
            "is_git_repo": is_git_repo,
            "current_branch": self.git_service.current_branch(root) if is_git_repo else None,
            "branches": self.git_service.list_branches(root) if is_git_repo else [],
            "git_status": git_status,
            "dirty": bool(git_status and git_status.dirty),
        }
        return WorkspaceInfo.model_validate(payload)

    def _safe_workspace_from_record(self, record: dict[str, Any]) -> WorkspaceInfo | None:
        try:
            return self._workspace_from_record(record)
        except WorkspacePathError:
            return None

    def _load_registry(self) -> dict[str, Any]:
        raw = self.storage.load()
        workspaces = raw.get("workspaces") if isinstance(raw.get("workspaces"), dict) else {}
        active_project_id = raw.get("active_project_id") if isinstance(raw.get("active_project_id"), str) else None
        cleaned: dict[str, dict[str, Any]] = {}
        for project_id, record in workspaces.items():
            if not isinstance(project_id, str) or not isinstance(record, dict):
                continue
            try:
                info = WorkspaceInfo.model_validate({**record, "is_git_repo": False})
            except ValidationError:
                continue
            cleaned[project_id] = info.model_dump(mode="json", exclude={"is_git_repo", "current_branch", "branches", "git_status", "dirty"})
        return {"active_project_id": active_project_id, "workspaces": cleaned}

    def _save_registry(self, registry: dict[str, Any]) -> None:
        self.storage.save(registry)

    @staticmethod
    def _record_for_project(registry: dict[str, Any], project_id: str) -> dict[str, Any]:
        record = registry["workspaces"].get(project_id)
        if not isinstance(record, dict):
            raise WorkspaceNotFoundError(f"Workspace is not registered: {project_id}")
        return dict(record)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
