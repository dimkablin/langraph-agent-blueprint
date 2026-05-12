"""P0 black-box tests for permission boundaries and denied tool results."""

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


class TestPermissionBehavior:
    def test_denied_shell_permission_is_reported_and_not_executed(
        self,
        runtime_factory,
        scripted_chat_model,
        dangerous_shell_denier,
        temp_project,
    ):
        important_file = temp_project / "important.txt"
        important_file.write_text("keep me\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Remove everything in the workspace."),
                ai_tool_call(
                    "bash",
                    {"command": "Remove-Item -Recurse -Force ."},
                    call_id="dangerous_shell",
                ),
                expect_tool_result("dangerous_shell", contains="Permission denied"),
                ai_final(
                    "The destructive shell command was blocked by permissions. "
                    "Changed files: none. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: user approval is required for destructive commands."
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

        result = runtime.run(AgentRunInput(message="Remove everything in the workspace.", project_root=str(temp_project)))

        assert result.status == "blocked"
        assert_file_content(important_file, "keep me\n")
        assert shell.executed_commands == []
        assert "blocked by permissions" in result.final_response
        model.assert_no_unused_steps()

    def test_denied_protected_file_edit_is_reported_and_file_is_unchanged(
        self,
        runtime_factory,
        scripted_chat_model,
        protected_file_denier,
        temp_project,
    ):
        env_file = temp_project / ".env"
        env_file.write_text("SECRET=keep\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Update the secret."),
                ai_tool_call("read_file", {"path": ".env"}, call_id="read_env"),
                expect_tool_result("read_env", contains="SECRET=keep"),
                ai_tool_call(
                    "edit_file",
                    {"path": ".env", "old_text": "SECRET=keep", "new_text": "SECRET=changed"},
                    call_id="edit_env",
                ),
                expect_tool_result("edit_env", contains="Permission denied"),
                ai_final(
                    "The protected file edit was blocked by permissions. "
                    "Changed files: none. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: explicit approval is required for protected file edits."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=protected_file_denier)

        result = runtime.run(AgentRunInput(message="Update the secret.", project_root=str(temp_project)))

        assert result.status == "blocked"
        assert_file_content(env_file, "SECRET=keep\n")
        assert result.changed_files == []
        assert "blocked by permissions" in result.final_response
        model.assert_no_unused_steps()
