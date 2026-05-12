"""P0 black-box tests for plan-mode safety behavior."""

from __future__ import annotations

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import (
    ai_final,
    ai_tool_call,
    assert_file_content,
    expect_tool_result,
    expect_user_message,
    recording_shell_executor,
)


class TestPlanModeBehavior:
    def test_plan_mode_blocks_edit_and_returns_plan_without_file_changes(
        self,
        runtime_factory,
        scripted_chat_model,
        plan_mode_permissions,
        temp_project,
    ):
        source = temp_project / "src" / "service.py"
        source.parent.mkdir()
        source.write_text("def is_enabled():\n    return False\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Plan the change before editing."),
                ai_tool_call("read_file", {"path": "src/service.py"}, call_id="read_service"),
                expect_tool_result("read_service", contains="return False"),
                ai_tool_call(
                    "edit_file",
                    {"path": "src/service.py", "old_text": "return False", "new_text": "return True"},
                    call_id="blocked_edit",
                ),
                expect_tool_result("blocked_edit", contains="plan mode blocks side effects"),
                ai_final(
                    "Plan: update src/service.py so is_enabled() returns True, then run python -m pytest -q. "
                    "Changed files: none. "
                    "Verification command: python -m pytest -q planned but not run. "
                    "Verification status: not run. "
                    "Remaining limitations: implementation requires approval to exit plan mode."
                ),
            ]
        )
        shell = recording_shell_executor()
        runtime = runtime_factory(
            project_root=temp_project,
            chat_model=model,
            permissions=plan_mode_permissions,
            shell_executor=shell,
        )

        result = runtime.run(
            AgentRunInput(
                message="Plan the change before editing.",
                project_root=str(temp_project),
                mode="plan",
            )
        )

        assert result.status == "blocked"
        assert_file_content(source, "def is_enabled():\n    return False\n")
        assert shell.executed_commands == []
        assert result.changed_files == []
        assert result.verification_commands == []
        assert result.verification_status == "not run"
        assert "src/service.py" in result.final_response
        assert "python -m pytest -q" in result.final_response
        assert "Remaining limitations" in result.final_response
        assert "requires approval" in result.final_response
        model.assert_no_unused_steps()
