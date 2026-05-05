from __future__ import annotations

import shlex
from pathlib import Path

from claude_code_langgraph.utils.platform import is_windows
from claude_code_langgraph.utils.subprocesses import run_subprocess
from claude_code_langgraph.utils.truncation import truncate_text


class ShellService:
    """Shell execution wrapper with timeout, cwd confinement, and output limits."""

    risky_tokens = {"rm", "del", "erase", "format", "shutdown", "restart-computer", "remove-item", "git reset"}

    def __init__(self, project_root: str | Path, timeout: float = 30.0, output_limit: int = 12000) -> None:
        self.project_root = Path(project_root).resolve()
        self.timeout = timeout
        self.output_limit = output_limit

    def classify(self, command: str) -> str:
        lowered = command.lower()
        return "dangerous" if any(token in lowered for token in self.risky_tokens) else "shell"

    def run(self, command: str, cwd: str | Path | None = None, powershell: bool = False) -> dict[str, object]:
        workdir = Path(cwd or self.project_root).resolve()
        try:
            workdir.relative_to(self.project_root)
        except ValueError as exc:
            raise PermissionError(f"Shell cwd is outside project root: {workdir}") from exc
        if powershell or is_windows():
            args: list[str] | str = ["powershell", "-NoProfile", "-Command", command] if not is_windows() else command
            shell = is_windows()
        else:
            args = command if isinstance(command, str) else shlex.join(command)
            shell = True
        completed = run_subprocess(args, workdir, self.timeout, shell=shell)
        stdout, stdout_truncated = truncate_text(completed.stdout, self.output_limit)
        stderr, stderr_truncated = truncate_text(completed.stderr, self.output_limit)
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": completed.returncode,
            "truncated": stdout_truncated or stderr_truncated,
            "classification": self.classify(command),
        }

