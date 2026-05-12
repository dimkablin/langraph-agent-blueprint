"""Reusable black-box test utilities for P0 agent runtime behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from langgraph_agent_blueprint.models import ModelRequest, ModelResponse, PermissionCheck, Usage


@dataclass(frozen=True)
class ExpectUserMessage:
    content: str


@dataclass(frozen=True)
class ExpectToolResult:
    tool_call_id: str
    contains: str | None = None


@dataclass(frozen=True)
class ExpectAnyMessage:
    contains: str


@dataclass(frozen=True)
class ToolCallResponse:
    name: str
    args: dict[str, Any]
    call_id: str


@dataclass(frozen=True)
class FinalResponse:
    content: str


ScriptedStep = ExpectUserMessage | ExpectToolResult | ExpectAnyMessage | ToolCallResponse | FinalResponse


class ScriptedChatModel:
    """Deterministic model provider that validates real graph messages between turns."""

    def __init__(self, steps: list[ScriptedStep]) -> None:
        self._steps = list(steps)
        self._cursor = 0

    def generate(self, request: ModelRequest) -> ModelResponse:
        while self._cursor < len(self._steps):
            step = self._steps[self._cursor]
            if isinstance(step, ExpectUserMessage):
                _assert_latest_human_message(request.messages, step.content)
                self._cursor += 1
                continue
            if isinstance(step, ExpectToolResult):
                _assert_tool_result(request.messages, step.tool_call_id, step.contains)
                self._cursor += 1
                continue
            if isinstance(step, ExpectAnyMessage):
                _assert_any_message(request.messages, step.contains)
                self._cursor += 1
                continue
            if isinstance(step, ToolCallResponse):
                self._cursor += 1
                tool_call = {"id": step.call_id, "name": step.name, "args": step.args}
                return ModelResponse(
                    content="",
                    tool_calls=[tool_call],
                    raw=AIMessage(content="", tool_calls=[tool_call]),
                    usage=_usage(step.name),
                )
            if isinstance(step, FinalResponse):
                self._cursor += 1
                return ModelResponse(content=step.content, raw=AIMessage(content=step.content), usage=_usage(step.content))
        raise AssertionError("ScriptedChatModel was called after all scripted steps were consumed.")

    def stream_generate(self, request: ModelRequest) -> list[Any]:
        raise AssertionError("P0 behavior tests use invoke(), not stream().")

    def assert_no_unused_steps(self) -> None:
        remaining = self._steps[self._cursor :]
        assert remaining == [], f"Unused scripted model steps: {remaining!r}"


def expect_user_message(content: str) -> ExpectUserMessage:
    return ExpectUserMessage(content)


def expect_tool_result(tool_call_id: str, *, contains: str | None = None) -> ExpectToolResult:
    return ExpectToolResult(tool_call_id, contains)


def expect_any_message(*, contains: str) -> ExpectAnyMessage:
    return ExpectAnyMessage(contains)


def ai_tool_call(name: str, args: dict[str, Any], *, call_id: str) -> ToolCallResponse:
    return ToolCallResponse(name=name, args=args, call_id=call_id)


def ai_final(content: str) -> FinalResponse:
    return FinalResponse(content)


@dataclass(frozen=True)
class ShellRun:
    stdout: str
    stderr: str = ""
    exit_code: int = 0


class ScriptedShellExecutor:
    """Controlled shell service replacement that records observable command execution."""

    def __init__(self, responses: dict[str, list[ShellRun]]) -> None:
        self._responses = {command: list(results) for command, results in responses.items()}
        self.executed_commands: list[str] = []

    def run(self, command: str, cwd: str | Path | None = None, powershell: bool = False) -> dict[str, object]:
        self.executed_commands.append(command)
        if command not in self._responses or not self._responses[command]:
            raise AssertionError(f"Unexpected shell command: {command}")
        result = self._responses[command].pop(0)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "truncated": False,
            "classification": "shell",
        }


class RecordingShellExecutor:
    """Shell service replacement used when denied actions must never execute."""

    def __init__(self) -> None:
        self.executed_commands: list[str] = []

    def run(self, command: str, cwd: str | Path | None = None, powershell: bool = False) -> dict[str, object]:
        self.executed_commands.append(command)
        return {"stdout": "", "stderr": "unexpected execution", "exit_code": 1, "truncated": False, "classification": "shell"}


def scripted_shell(responses: dict[str, list[ShellRun]]) -> ScriptedShellExecutor:
    return ScriptedShellExecutor(responses)


def recording_shell_executor() -> RecordingShellExecutor:
    return RecordingShellExecutor()


def shell_ok(stdout: str) -> ShellRun:
    return ShellRun(stdout=stdout, exit_code=0)


def shell_error(stderr: str) -> ShellRun:
    return ShellRun(stdout="", stderr=stderr, exit_code=1)


class AllowAllPermissions:
    def decide(self, tool: Any, state: dict[str, Any], args: dict[str, Any]) -> PermissionCheck:
        return PermissionCheck(decision="allow", reason="test approval allows this tool")


@dataclass(frozen=True)
class DenyRule:
    action: str | None = None
    path: str | None = None
    command_contains: str | None = None
    reason: str = "Permission denied by test policy."


@dataclass
class DenyingPermissions:
    rules: list[DenyRule] = field(default_factory=list)

    def decide(self, tool: Any, state: dict[str, Any], args: dict[str, Any]) -> PermissionCheck:
        action = getattr(getattr(tool, "permission", None), "action", None)
        for rule in self.rules:
            if rule.action is not None and rule.action != action:
                continue
            if rule.path is not None and str(args.get("path")) != rule.path:
                continue
            if rule.command_contains is not None and rule.command_contains.lower() not in str(args.get("command", "")).lower():
                continue
            return PermissionCheck(decision="deny", reason=rule.reason)
        return PermissionCheck(decision="allow", reason="test policy allows this tool")


class PlanModePermissions:
    def decide(self, tool: Any, state: dict[str, Any], args: dict[str, Any]) -> PermissionCheck:
        permission = getattr(tool, "permission", None)
        if state.get("plan_mode", {}).get("enabled") and permission is not None and not permission.is_read_only:
            return PermissionCheck(decision="deny", reason="plan mode blocks side effects until implementation approval")
        return PermissionCheck(decision="allow", reason="read-only or approved plan-mode action")


def assert_final_response_contract(
    result: Any,
    *,
    changed_files: list[str],
    verification_commands: list[str],
    verification_status: Literal["passed", "failed", "not run"],
    remaining_limitations: str,
) -> None:
    assert result.status in {"success", "error", "blocked"}
    assert result.changed_files == changed_files
    assert result.verification_commands == verification_commands
    assert result.verification_status == verification_status
    for path in changed_files:
        assert path in result.final_response
    for command in verification_commands:
        assert command in result.final_response
    assert "Remaining limitations" in result.final_response
    assert remaining_limitations in result.final_response


def assert_file_content(path: Path, expected: str) -> None:
    assert path.read_text(encoding="utf-8") == expected


def _assert_latest_human_message(messages: list[Any], expected: str) -> None:
    human_messages = [message for message in messages if isinstance(message, HumanMessage)]
    assert human_messages, f"Expected HumanMessage containing {expected!r}; messages were {messages!r}"
    latest = str(human_messages[-1].content)
    assert expected in latest


def _assert_tool_result(messages: list[Any], tool_call_id: str, contains: str | None) -> None:
    tool_messages = [
        message
        for message in messages
        if isinstance(message, ToolMessage) and getattr(message, "tool_call_id", None) == tool_call_id
    ]
    assert tool_messages, f"Expected ToolMessage for {tool_call_id!r}; messages were {messages!r}"
    content = str(tool_messages[-1].content)
    if contains is not None:
        assert contains in content


def _assert_any_message(messages: list[Any], expected: str) -> None:
    rendered = "\n".join(_message_content(message) for message in messages)
    assert expected in rendered


def _message_content(message: BaseMessage) -> str:
    return str(getattr(message, "content", ""))


def _usage(text: str) -> Usage:
    token_count = max(1, len(text) // 4)
    return Usage(input_tokens=token_count, output_tokens=token_count, total_tokens=token_count * 2)
