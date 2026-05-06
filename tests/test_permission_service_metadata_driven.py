"""Tests that permission policy uses tool metadata rather than tool names."""

from __future__ import annotations

from pydantic import BaseModel

from claude_code_langgraph.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata
from claude_code_langgraph.models.tools import ToolCall
from claude_code_langgraph.services.permission_service import PermissionService, redact_args, summarize_args
from claude_code_langgraph.tools.base import BaseTool, ToolExecutionContext, ToolOutput


class CustomInput(BaseModel):
    command: str = ""
    api_key: str = ""
    nested: dict[str, object] = {}


class CustomOutput(ToolOutput):
    pass


class CustomDangerousTool(BaseTool[CustomInput, CustomOutput]):
    name = "totally_new_tool"
    description = "A custom dangerous tool whose name is intentionally not known to PermissionService."
    input_schema = CustomInput
    output_schema = CustomOutput
    permission = ToolPermissionMetadata(
        action="shell",
        risk="high",
        requires_permission=True,
        reason="custom dangerous tool",
        sensitive_arg_keys={"api_key"},
    )
    runtime = ToolRuntimeMetadata(kind="custom", route="execute")

    def run(self, data: CustomInput, context: ToolExecutionContext) -> CustomOutput:
        return CustomOutput(content="ok")


class CustomSafeReadTool(CustomDangerousTool):
    name = "whatever_name"
    permission = ToolPermissionMetadata(action="read", risk="low", is_read_only=True, allowed_in_plan_mode=True)


def test_permission_service_decides_from_metadata_for_unknown_dangerous_tool():
    tool = CustomDangerousTool()
    decision = PermissionService().decide(tool, {"plan_mode": {"enabled": False}}, {"command": "x"})

    assert decision.decision == "ask"
    assert decision.reason == "custom dangerous tool"


def test_permission_service_allows_metadata_safe_read_tool_in_default_and_plan_mode():
    tool = CustomSafeReadTool()

    assert PermissionService().decide(tool, {"plan_mode": {"enabled": False}}, {}).decision == "allow"
    assert PermissionService().decide(tool, {"plan_mode": {"enabled": True}}, {}).decision == "allow"


def test_confirmation_payload_uses_tool_metadata_and_redacts_sensitive_args():
    tool = CustomDangerousTool()
    call = ToolCall(
        id="call_1",
        name=tool.name,
        args={"command": "run", "api_key": "secret-value", "nested": {"token": "secret-token", "safe": "ok"}},
    )

    payload = PermissionService.confirmation_payload(call, tool, "needs approval").model_dump(mode="json")

    assert payload["action"] == "shell"
    assert payload["risk"] == "high"
    assert payload["args"]["api_key"] == "***"
    assert payload["args"]["nested"]["token"] == "***"
    assert "secret-value" not in payload["args_summary"]
    assert "secret-token" not in payload["args_summary"]


def test_arg_redaction_is_recursive_and_summary_is_stable_json():
    args = {"z": "last", "password": "secret", "nested": {"authorization": "bearer", "a": 1}}

    redacted = redact_args(args, {"password"})
    summary = summarize_args(args, sensitive_keys={"password"}, limit=80)

    assert redacted == {"z": "last", "password": "***", "nested": {"authorization": "***", "a": 1}}
    assert summary.startswith('{"nested"')
    assert "secret" not in summary
    assert "bearer" not in summary
