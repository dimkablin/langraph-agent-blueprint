"""Typed workspace and Git metadata contracts."""

from __future__ import annotations

from pydantic import Field

from .base import RuntimeModel


class GitStatusSummary(RuntimeModel):
    """Small, stable summary of a Git working tree status."""

    staged: int = 0
    unstaged: int = 0
    untracked: int = 0
    conflicted: int = 0

    @property
    def dirty(self) -> bool:
        return self.staged > 0 or self.unstaged > 0 or self.untracked > 0 or self.conflicted > 0

    @property
    def has_conflicts(self) -> bool:
        return self.conflicted > 0


class WorkspaceInfo(RuntimeModel):
    """Public workspace/project metadata exposed to runtime and frontend clients."""

    project_id: str
    display_name: str
    root_path: str
    is_git_repo: bool = False
    current_branch: str | None = None
    branches: list[str] = Field(default_factory=list)
    git_status: GitStatusSummary | None = None
    dirty: bool = False
    created_at: str | None = None
    last_opened_at: str | None = None


class WorkspaceCheckoutResult(RuntimeModel):
    """Result of a safe branch checkout attempt."""

    ok: bool
    workspace: WorkspaceInfo
    message: str
