"""P0 black-box tests for invalid tool calls and tool execution failures."""

from __future__ import annotations

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import ai_final, ai_tool_call, expect_tool_result, expect_user_message


class TestToolErrorBehavior:
    def test_unknown_tool_call_returns_clear_terminal_error(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        model = scripted_chat_model(
            steps=[
                expect_user_message("Use a missing tool."),
                ai_tool_call("missing_tool", {"value": "x"}, call_id="missing_tool_call"),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Use a missing tool.", project_root=str(temp_project)))

        assert result.status == "error"
        assert result.error_message is not None
        assert "Unknown tool" in result.error_message
        assert "Unknown tool" in result.final_response
        model.assert_no_unused_steps()

    def test_repeated_invalid_tool_arguments_return_terminal_error_after_recovery_limit(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        model = scripted_chat_model(
            steps=[
                expect_user_message("Keep reading with invalid arguments."),
                ai_tool_call("read_file", {"missing_path": "README.md"}, call_id="invalid_read_1"),
                expect_tool_result("invalid_read_1", contains="Field required"),
                ai_tool_call("read_file", {"missing_path": "README.md"}, call_id="invalid_read_2"),
                expect_tool_result("invalid_read_2", contains="Field required"),
                ai_tool_call("read_file", {"missing_path": "README.md"}, call_id="invalid_read_3"),
                expect_tool_result("invalid_read_3", contains="Field required"),
                ai_tool_call("read_file", {"missing_path": "README.md"}, call_id="invalid_read_4"),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Keep reading with invalid arguments.", project_root=str(temp_project)))

        assert result.status == "error"
        assert result.changed_files == []
        assert result.error_message is not None
        assert "Maximum recoverable tool error attempts exceeded" in result.error_message
        assert "Field required" in result.error_message
        assert "Recovered from error" in result.final_response
        model.assert_no_unused_steps()

    def test_invalid_tool_arguments_are_returned_to_model_as_tool_result(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        model = scripted_chat_model(
            steps=[
                expect_user_message("Read with invalid arguments and explain the failure."),
                ai_tool_call("read_file", {"missing_path": "README.md"}, call_id="invalid_read"),
                expect_tool_result("invalid_read", contains="Field required"),
                ai_final(
                    "The read_file tool call failed because the required path argument was missing. "
                    "Changed files: none. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: a valid path argument is required."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(
            AgentRunInput(
                message="Read with invalid arguments and explain the failure.",
                project_root=str(temp_project),
            )
        )

        model.assert_no_unused_steps()
        assert result.status == "success"
        assert result.changed_files == []
        assert result.error_message is None
        assert "required path argument was missing" in result.final_response
