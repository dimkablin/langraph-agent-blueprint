"""Safe, read-focused Git operations for workspace metadata."""

from __future__ import annotations

import subprocess
from pathlib import Path

from langgraph_agent_blueprint.models import GitStatusSummary


class GitServiceError(RuntimeError):
    """Base error for safe Git service operations."""


class GitCheckoutBlockedError(GitServiceError):
    """Raised when checkout is blocked to avoid losing user work."""


class GitBranchNotFoundError(GitServiceError):
    """Raised when a requested branch is not an existing local branch."""


class GitService:
    """Minimal Git adapter that never runs destructive operations."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def is_git_repo(self, root: str | Path) -> bool:
        try:
            if self._git(root, "rev-parse", "--is-inside-work-tree") != "true":
                return False
            top_level = Path(self._git(root, "rev-parse", "--show-toplevel")).resolve()
            return top_level == Path(root).resolve()
        except GitServiceError:
            return False

    def current_branch(self, root: str | Path) -> str | None:
        if not self.is_git_repo(root):
            return None
        branch = self._git(root, "branch", "--show-current")
        return branch or None

    def list_branches(self, root: str | Path) -> list[str]:
        if not self.is_git_repo(root):
            return []
        output = self._git(root, "branch", "--format=%(refname:short)")
        return sorted(line.strip() for line in output.splitlines() if line.strip())

    def status_summary(self, root: str | Path) -> GitStatusSummary:
        if not self.is_git_repo(root):
            return GitStatusSummary()
        output = self._git(root, "status", "--porcelain=v1")
        return _parse_status_summary(output)

    def checkout_existing_branch(self, root: str | Path, branch: str, *, confirm_dirty: bool = False) -> None:
        branches = self.list_branches(root)
        if branch not in branches:
            raise GitBranchNotFoundError(f"Git branch does not exist: {branch}")
        status = self.status_summary(root)
        if status.dirty and not confirm_dirty:
            raise GitCheckoutBlockedError("Workspace has uncommitted changes; explicit confirmation is required before checkout.")
        self._git(root, "checkout", branch)

    def _git(self, root: str | Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(Path(root).resolve()), *args],
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
            raise GitServiceError(message)
        return completed.stdout.strip()


def _parse_status_summary(output: str) -> GitStatusSummary:
    staged = 0
    unstaged = 0
    untracked = 0
    conflicted = 0
    conflict_codes = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
    for line in output.splitlines():
        if len(line) < 2:
            continue
        code = line[:2]
        if code == "??":
            untracked += 1
            continue
        if code in conflict_codes or "U" in code:
            conflicted += 1
            continue
        if code[0] != " ":
            staged += 1
        if code[1] != " ":
            unstaged += 1
    return GitStatusSummary(staged=staged, unstaged=unstaged, untracked=untracked, conflicted=conflicted)
