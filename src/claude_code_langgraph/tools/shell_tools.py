"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel

from claude_code_langgraph.services.shell_service import ShellService

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class ShellInput(BaseModel):
    """Pydantic input schema for the shell operation."""
    command: str
    cwd: str | None = None


class ShellOutput(ToolOutput):
    """Pydantic output schema for the shell operation."""
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
    safety = ToolSafety.SHELL
    is_read_only = False
    requires_permission = True

    def __init__(self, shell_service: ShellService) -> None:
        self.shell_service = shell_service

    def run(self, data: ShellInput, context: ToolExecutionContext) -> ShellOutput:
        result = self.shell_service.run(data.command, data.cwd or context.cwd, powershell=False)
        return ShellOutput(
            ok=result["exit_code"] == 0,
            content=str(result["stdout"] or result["stderr"]),
            stdout=str(result["stdout"]),
            stderr=str(result["stderr"]),
            exit_code=int(result["exit_code"]),
            truncated=bool(result["truncated"]),
            metadata={"classification": result["classification"]},
        )


class PowerShellTool(BashTool):
    """Windows PowerShell variant of the shell tool with the same permission model."""
    name = "powershell"
    description = "Execute a Windows PowerShell command with the same permission model as BashTool."

    def run(self, data: ShellInput, context: ToolExecutionContext) -> ShellOutput:
        result = self.shell_service.run(data.command, data.cwd or context.cwd, powershell=True)
        return ShellOutput(
            ok=result["exit_code"] == 0,
            content=str(result["stdout"] or result["stderr"]),
            stdout=str(result["stdout"]),
            stderr=str(result["stderr"]),
            exit_code=int(result["exit_code"]),
            truncated=bool(result["truncated"]),
            metadata={"classification": result["classification"]},
        )

