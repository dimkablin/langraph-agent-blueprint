"""FastAPI contract tests for workspace selection and Git branch operations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def test_workspace_api_adds_selects_and_returns_active_workspace(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    client = _client(tmp_path)

    added = client.post("/workspaces", json={"root_path": str(workspace_root)}).json()
    active = client.get("/workspaces/active").json()
    selected = client.post("/workspaces/select", json={"project_id": added["project_id"]}).json()

    assert added["root_path"] == str(workspace_root.resolve())
    assert added["is_git_repo"] is False
    assert active["project_id"] == added["project_id"]
    assert selected["project_id"] == added["project_id"]


def test_workspace_api_rejects_invalid_local_paths(tmp_path: Path) -> None:
    client = _client(tmp_path)
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("content", encoding="utf-8")

    missing = client.post("/workspaces", json={"root_path": str(tmp_path / "missing")})
    file_response = client.post("/workspaces", json={"root_path": str(file_path)})

    assert missing.status_code == 400
    assert file_response.status_code == 400


def test_workspace_api_ignores_stale_active_workspace(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    missing_root = tmp_path / "missing-workspace"
    project_id = f"project_missing_{missing_root.name}"
    _write_workspace_registry(
        storage,
        active_project_id=project_id,
        workspaces={
            project_id: {
                "project_id": project_id,
                "display_name": "missing-workspace",
                "root_path": str(missing_root),
            }
        },
    )
    client = _client(tmp_path)

    workspaces = client.get("/workspaces")
    active = client.get("/workspaces/active")

    assert workspaces.status_code == 200
    assert workspaces.json() == []
    assert active.status_code == 200
    assert active.json() is None


def test_chat_api_reports_deleted_workspace_folder(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    missing_root = tmp_path / "deleted-workspace"
    project_id = f"project_missing_{missing_root.name}"
    _write_workspace_registry(
        storage,
        active_project_id=None,
        workspaces={
            project_id: {
                "project_id": project_id,
                "display_name": "deleted-workspace",
                "root_path": str(missing_root),
            }
        },
    )
    client = _client(tmp_path)

    response = client.post("/chat", json={"message": "hello", "project_id": project_id})

    assert response.status_code == 400
    assert "Workspace path does not exist" in response.json()["detail"]


def test_workspace_api_can_pick_folder_through_public_picker_service(tmp_path: Path) -> None:
    workspace_root = tmp_path / "picked-workspace"
    workspace_root.mkdir()
    client = _client(tmp_path)
    client.app.state.runtime.dependencies.folder_picker_service = _FakeFolderPicker(workspace_root)

    picked = client.post("/workspaces/pick").json()
    active = client.get("/workspaces/active").json()

    assert picked["root_path"] == str(workspace_root.resolve())
    assert picked["project_id"] == active["project_id"]


def test_workspace_api_returns_null_when_folder_picker_is_cancelled(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.runtime.dependencies.folder_picker_service = _FakeFolderPicker(None)

    response = client.post("/workspaces/pick")

    assert response.status_code == 200
    assert response.json() is None


def test_workspace_api_exposes_git_branches_and_blocks_dirty_checkout(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    _git(repo, "checkout", "-b", "feature")
    _git(repo, "checkout", "master")
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")
    client = _client(tmp_path)
    workspace = client.post("/workspaces", json={"root_path": str(repo)}).json()

    branches = client.get(f"/workspaces/{workspace['project_id']}/branches").json()
    blocked = client.post(f"/workspaces/{workspace['project_id']}/checkout", json={"branch": "feature"})

    assert set(branches) >= {"master", "feature"}
    assert blocked.status_code == 409
    assert _git(repo, "branch", "--show-current") == "master"
    assert (repo / "README.md").read_text(encoding="utf-8") == "dirty\n"


def test_chat_and_session_routes_use_active_workspace_root(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    client = _client(tmp_path)
    workspace = client.post("/workspaces", json={"root_path": str(workspace_root)}).json()

    chat = client.post("/chat", json={"message": "hello", "project_id": workspace["project_id"]}).json()
    sessions = client.get("/sessions").json()

    assert chat["session_id"]
    assert [item["session_id"] for item in sessions] == [chat["session_id"]]


def _client(tmp_path: Path) -> TestClient:
    app_root = tmp_path / "app"
    app_root.mkdir(exist_ok=True)
    config = AppConfig(storage_dir=tmp_path / "storage", project_root=app_root, cwd=app_root, llm_provider="fake")
    return TestClient(create_app(config))


class _FakeFolderPicker:
    def __init__(self, selected_path: Path | None) -> None:
        self.selected_path = selected_path

    def select_directory(self, *, title: str) -> Path | None:
        assert title
        return self.selected_path


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
