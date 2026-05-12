"""P0 behavior tests for frontend-visible agent activity events."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from langgraph_agent_blueprint.models import AgentRunInput, ToolActivitySpec
from langgraph_agent_blueprint.tools.base import BaseTool, ToolExecutionContext, ToolOutput

from .helpers import (
    ai_final,
    ai_tool_call,
    expect_any_message,
    expect_tool_result,
    expect_user_message,
    recording_shell_executor,
    scripted_shell,
    shell_ok,
)


class CustomProbeInput(BaseModel):
    phrase: str


class CustomProbeOutput(ToolOutput):
    observed: str


class CustomProbeTool(BaseTool[CustomProbeInput, CustomProbeOutput]):
    name = "custom_probe"
    description = "Custom test probe."
    input_schema = CustomProbeInput
    output_schema = CustomProbeOutput
    activity = ToolActivitySpec(
        display_name="Custom Probe",
        started_type="custom.probe.started",
        completed_type="custom.probe.completed",
        failed_type="custom.probe.failed",
    )

    def run(self, data: CustomProbeInput, context: ToolExecutionContext) -> CustomProbeOutput:
        return CustomProbeOutput(content=f"observed {data.phrase}", observed=data.phrase)

    def activity_started_data(self, data: CustomProbeInput, context: ToolExecutionContext) -> dict[str, Any]:
        return {"phrase": data.phrase}

    def activity_completed_data(
        self,
        data: CustomProbeInput,
        output: CustomProbeOutput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        return {"observed": output.observed}


class TestAgentActivityBehavior:
    def test_custom_tool_owned_activity_types_flow_through_public_runtime(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ) -> None:
        model = scripted_chat_model(
            steps=[
                expect_user_message("Run the custom probe."),
                ai_tool_call("custom_probe", {"phrase": "hello"}, call_id="probe_call"),
                expect_tool_result("probe_call", contains="observed hello"),
                ai_final(
                    "Custom probe finished. Changed files: none. "
                    "Verification command: not run. Verification status: not run. "
                    "Remaining limitations: custom probe only."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)
        runtime.dependencies.tool_registry.register(CustomProbeTool())

        result = runtime.run(AgentRunInput(message="Run the custom probe.", project_root=str(temp_project)))
        activity_types = [item["type"] for item in _activities(result.events)]

        assert "custom.probe.started" in activity_types
        assert "custom.probe.completed" in activity_types
        assert all(activity["data"].get("tool_name") != "bash" for activity in _activities(result.events))
        model.assert_no_unused_steps()

    def test_file_activity_includes_path_without_file_content(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ) -> None:
        secret = "SECRET_VALUE_SHOULD_NOT_LEAK"
        (temp_project / "secrets.txt").write_text(f"public\n{secret}\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Read the file."),
                ai_tool_call("read_file", {"path": "secrets.txt"}, call_id="read_secret"),
                expect_tool_result("read_secret", contains=secret),
                ai_final(
                    "File read. Changed files: none. Verification command: not run. "
                    "Verification status: not run. Remaining limitations: none."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Read the file.", project_root=str(temp_project)))
        activity_payload = json.dumps(_activities(result.events), sort_keys=True)

        assert "secrets.txt" in activity_payload
        assert secret not in activity_payload
        assert any(activity["type"] == "tool.read_file.completed" for activity in _activities(result.events))

    def test_shell_activity_includes_command_exit_code_and_bounded_output(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ) -> None:
        long_stdout = "x" * 1600
        model = scripted_chat_model(
            steps=[
                expect_user_message("Run verification."),
                ai_tool_call("bash", {"command": "pytest -q"}, call_id="pytest_call"),
                expect_tool_result("pytest_call", contains=long_stdout),
                ai_final(
                    "Verification ran. Changed files: none. Verification command: pytest -q. "
                    "Verification status: passed. Remaining limitations: none."
                ),
            ]
        )
        runtime = runtime_factory(
            project_root=temp_project,
            chat_model=model,
            permissions=approving_permissions,
            shell_executor=scripted_shell({"pytest -q": [shell_ok(long_stdout)]}),
        )

        result = runtime.run(AgentRunInput(message="Run verification.", project_root=str(temp_project)))
        shell_activity = _activity_by_type(result.events, "tool.bash.completed")
        activity_payload = json.dumps(shell_activity, sort_keys=True)

        assert shell_activity["category"] == "verification"
        assert shell_activity["data"]["command"] == "pytest -q"
        assert shell_activity["data"]["exit_code"] == 0
        assert long_stdout not in activity_payload

    def test_permission_denial_emits_blocked_activity(
        self,
        runtime_factory,
        scripted_chat_model,
        dangerous_shell_denier,
        temp_project,
    ) -> None:
        model = scripted_chat_model(
            steps=[
                expect_user_message("Remove everything."),
                ai_tool_call("bash", {"command": "Remove-Item -Recurse -Force ."}, call_id="dangerous_shell"),
                expect_tool_result("dangerous_shell", contains="Permission denied"),
                ai_final(
                    "Blocked. Changed files: none. Verification command: not run. "
                    "Verification status: not run. Remaining limitations: approval required."
                ),
            ]
        )
        shell = recording_shell_executor()
        runtime = runtime_factory(
            project_root=temp_project,
            chat_model=model,
            permissions=dangerous_shell_denier,
            shell_executor=shell,
        )

        result = runtime.run(AgentRunInput(message="Remove everything.", project_root=str(temp_project)))
        blocked = _activity_by_type(result.events, "permission.tool.denied")

        assert blocked["category"] == "permission"
        assert blocked["status"] == "blocked"
        assert "Permission denied" in blocked.get("summary", "")
        assert shell.executed_commands == []

    def test_skill_activation_emits_safe_activity_without_skill_body(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ) -> None:
        model = scripted_chat_model(
            steps=[
                expect_user_message("Use the verification skill."),
                ai_tool_call(
                    "skill",
                    {"skill": "verify", "args": {"task": "check tests", "commands": ["pytest -q"]}},
                    call_id="skill_verify",
                ),
                expect_tool_result("skill_verify", contains="verify"),
                expect_any_message(contains="Identify the command"),
                ai_final(
                    "Skill prepared. Changed files: none. Verification command: not run. "
                    "Verification status: not run. Remaining limitations: none."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Use the verification skill.", project_root=str(temp_project)))
        skill_activities = [activity for activity in _activities(result.events) if activity["category"] == "skill"]
        activity_payload = json.dumps(skill_activities, sort_keys=True)

        assert any(activity["type"] == "skill.verify.loading" for activity in skill_activities)
        assert any(activity["type"] == "skill.verify.activated" for activity in skill_activities)
        assert "Identify the command that proves the claim" not in activity_payload
        assert "prompt" not in activity_payload


def _activities(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    activities: list[dict[str, Any]] = []
    for item in events:
        data = item.get("data")
        if isinstance(data, dict) and isinstance(data.get("activity"), dict):
            activities.append(data["activity"])
    return activities


def _activity_by_type(events: list[dict[str, Any]], activity_type: str) -> dict[str, Any]:
    for activity in _activities(events):
        if activity.get("type") == activity_type:
            return activity
    raise AssertionError(f"Missing activity {activity_type!r}; saw {[item.get('type') for item in _activities(events)]}")
