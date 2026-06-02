"""Behavior tests for public workspace selection and Git awareness services."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from langgraph_agent_blueprint.services.git_service import GitCheckoutBlockedError, GitService
from langgraph_agent_blueprint.services.workspace_service import WorkspacePathError, WorkspaceService


def test_workspace_service_adds_valid_directory_with_normalized_root(tmp_path: Path) -> None:
    workspace_root = tmp_path / "project" / ".." / "project"
    workspace_root.resolve().mkdir(parents=True)
    service = WorkspaceService(tmp_path / "storage", git_service=GitService())

    workspace = service.add_workspace(workspace_root)

    assert workspace.root_path == str(workspace_root.resolve())
    assert workspace.display_name == "project"
    assert workspace.project_id
    assert service.get_active_workspace().project_id == workspace.project_id


def test_workspace_service_rejects_nonexistent_and_file_paths(tmp_path: Path) -> None:
    service = WorkspaceService(tmp_path / "storage", git_service=GitService())
    file_path = tmp_path / "README.md"
    file_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(WorkspacePathError, match="does not exist"):
        service.add_workspace(tmp_path / "missing")

    with pytest.raises(WorkspacePathError, match="not a directory"):
        service.add_workspace(file_path)


def test_workspace_service_ignores_stale_registered_workspaces(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    missing_root = tmp_path / "missing-project"
    project_id = WorkspaceService.project_id_for_root(missing_root)
    _write_workspace_registry(
        storage,
        active_project_id=project_id,
        workspaces={
            project_id: {
                "project_id": project_id,
                "display_name": "missing-project",
                "root_path": str(missing_root),
            }
        },
    )
    service = WorkspaceService(storage, git_service=GitService())

    assert service.list_workspaces() == []
    assert service.get_active_workspace() is None


def test_non_git_workspace_reports_no_git_metadata(tmp_path: Path) -> None:
    workspace_root = tmp_path / "plain"
    workspace_root.mkdir()
    service = WorkspaceService(tmp_path / "storage", git_service=GitService())

    workspace = service.add_workspace(workspace_root)

    assert workspace.is_git_repo is False
    assert workspace.current_branch is None
    assert workspace.branches == []
    assert workspace.git_status is None
    assert workspace.dirty is False


def test_git_workspace_reports_branch_list_and_dirty_status(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    _git(repo, "checkout", "-b", "feature")
    (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
    service = WorkspaceService(tmp_path / "storage", git_service=GitService())

    workspace = service.add_workspace(repo)

    assert workspace.is_git_repo is True
    assert workspace.current_branch == "feature"
    assert set(workspace.branches) >= {"master", "feature"}
    assert workspace.git_status is not None
    assert workspace.git_status.untracked == 1
    assert workspace.dirty is True


def test_checkout_existing_branch_works_on_clean_repo(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    _git(repo, "checkout", "-b", "feature")
    _git(repo, "checkout", "master")
    service = WorkspaceService(tmp_path / "storage", git_service=GitService())
    workspace = service.add_workspace(repo)

    result = service.checkout_branch(workspace.project_id, "feature")

    assert result.ok is True
    assert result.workspace.current_branch == "feature"
    assert _git(repo, "branch", "--show-current") == "feature"


def test_checkout_dirty_repo_is_blocked_without_discarding_user_changes(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    _git(repo, "checkout", "-b", "feature")
    _git(repo, "checkout", "master")
    tracked = repo / "README.md"
    tracked.write_text("user edits\n", encoding="utf-8")
    service = WorkspaceService(tmp_path / "storage", git_service=GitService())
    workspace = service.add_workspace(repo)

    with pytest.raises(GitCheckoutBlockedError, match="uncommitted changes"):
        service.checkout_branch(workspace.project_id, "feature")

    assert _git(repo, "branch", "--show-current") == "master"
    assert tracked.read_text(encoding="utf-8") == "user edits\n"


def test_checkout_dirty_repo_requires_explicit_confirmation(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    _git(repo, "checkout", "-b", "feature")
    _git(repo, "checkout", "master")
    (repo / "untracked.txt").write_text("safe to keep", encoding="utf-8")
    service = WorkspaceService(tmp_path / "storage", git_service=GitService())
    workspace = service.add_workspace(repo)

    result = service.checkout_branch(workspace.project_id, "feature", confirm_dirty=True)

    assert result.ok is True
    assert result.workspace.current_branch == "feature"
    assert (repo / "untracked.txt").read_text(encoding="utf-8") == "safe to keep"


def _init_git_repo(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "master")
    _git(path, "config", "user.email", "tests@example.test")
    _git(path, "config", "user.name", "Tests")
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    return path


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def _write_workspace_registry(storage: Path, *, active_project_id: str | None, workspaces: dict[str, dict[str, str]]) -> None:
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "workspaces.json").write_text(
        json.dumps({"active_project_id": active_project_id, "workspaces": workspaces}),
        encoding="utf-8",
    )
