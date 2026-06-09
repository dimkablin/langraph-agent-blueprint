"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models import ToolActivitySpec, ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services import ShellService
from langgraph_agent_blueprint.utils.activity import activity_text_summary
from langgraph_agent_blueprint.utils.path_contract import PROJECT_RELATIVE_CWD_DESCRIPTION

from .base import BaseTool, ToolExecutionContext, ToolOutput


class ShellInput(BaseModel):
    """Pydantic input schema for the shell operation."""
    command: str = Field(description="Shell command to execute.")
    cwd: str | None = Field(default=None, description=PROJECT_RELATIVE_CWD_DESCRIPTION)


class ShellOutput(ToolOutput):
    """Pydantic output schema for the shell operation."""
    command: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    truncated: bool = False


class BashTool(BaseTool[ShellInput, ShellOutput]):
    """Model-callable shell tool that executes commands behind permission and timeout policy."""
    name = "bash"
    description = "Execute a shell command with timeout and output truncation."
    input_schema = ShellInput
    output_schema = ShellOutput
    permission = ToolPermissionMetadata(action="shell", risk="high", requires_permission=True, reason="Shell commands can modify the system.")
    runtime = ToolRuntimeMetadata(kind="shell")
    activity = ToolActivitySpec(
        display_name="Run Bash command",
        started_type="tool.bash.started",
        completed_type="tool.bash.completed",
        failed_type="tool.bash.failed",
        blocked_type="tool.bash.blocked",
    )

    def __init__(self, shell_service: ShellService) -> None:
        self.shell_service = shell_service

    def run(self, data: ShellInput, context: ToolExecutionContext) -> ShellOutput:
        result = _shell_service_for_context(self.shell_service, context).run(data.command, data.cwd or context.cwd, powershell=False)
        return ShellOutput(
            ok=result["exit_code"] == 0,
            content=str(result["stdout"] or result["stderr"]),
            command=data.command,
            stdout=str(result["stdout"]),
            stderr=str(result["stderr"]),
            exit_code=int(result["exit_code"]),
            truncated=bool(result["truncated"]),
            metadata={"classification": result["classification"], "command": data.command},
        )

    def activity_category(
        self,
        *,
        data: ShellInput | None,
        output: ShellOutput | None,
        error: BaseException | None,
    ) -> str:
        command = output.command if output else data.command if data else ""
        return "verification" if _looks_like_verification_command(command) else self.activity_spec().category

    def activity_started_data(self, data: ShellInput | None, context: ToolExecutionContext) -> dict[str, object]:
        return {"operation": "shell.run", "command": data.command if data else "", "cwd": data.cwd if data else None}

    def activity_completed_data(self, data: ShellInput, output: ShellOutput, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "shell.run",
            "command": output.command,
            "exit_code": output.exit_code,
            "stdout_summary": activity_text_summary(output.stdout),
            "stderr_summary": activity_text_summary(output.stderr),
            "stdout_chars": len(output.stdout),
            "stderr_chars": len(output.stderr),
            "truncated": output.truncated,
            "classification": output.metadata.get("classification"),
        }

    def activity_started_summary(self, data: ShellInput | None, context: ToolExecutionContext) -> str | None:
        return f"Running `{data.command}`." if data else "Running shell command."

    def activity_completed_summary(self, data: ShellInput, output: ShellOutput, context: ToolExecutionContext) -> str | None:
        return f"Command exited with code {output.exit_code}."


class PowerShellTool(BashTool):
    """Windows PowerShell variant of the shell tool with the same permission model."""
    name = "powershell"
    description = "Execute a Windows PowerShell command with the same permission model as BashTool."
    activity = ToolActivitySpec(
        display_name="Run PowerShell command",
        started_type="tool.powershell.started",
        completed_type="tool.powershell.completed",
        failed_type="tool.powershell.failed",
        blocked_type="tool.powershell.blocked",
    )

    def run(self, data: ShellInput, context: ToolExecutionContext) -> ShellOutput:
        result = _shell_service_for_context(self.shell_service, context).run(data.command, data.cwd or context.cwd, powershell=True)
        return ShellOutput(
            ok=result["exit_code"] == 0,
            content=str(result["stdout"] or result["stderr"]),
            command=data.command,
            stdout=str(result["stdout"]),
            stderr=str(result["stderr"]),
            exit_code=int(result["exit_code"]),
            truncated=bool(result["truncated"]),
            metadata={"classification": result["classification"], "command": data.command},
        )


def _shell_service_for_context(shell_service: ShellService, context: ToolExecutionContext) -> ShellService:
    if not isinstance(shell_service, ShellService):
        return shell_service
    if shell_service.project_root == context.project_root:
        return shell_service
    return ShellService(context.project_root, timeout=shell_service.timeout, output_limit=shell_service.output_limit)


def _looks_like_verification_command(command: str) -> bool:
    normalized = command.strip().lower()
    if not normalized:
        return False
    starters = (
        "pytest",
        "python -m pytest",
        "npm test",
        "npm run test",
        "npm run build",
        "npm run lint",
        "node --test",
        "uv run pytest",
        "ruff",
        "mypy",
        "tsc",
    )
    return any(normalized.startswith(starter) for starter in starters)

