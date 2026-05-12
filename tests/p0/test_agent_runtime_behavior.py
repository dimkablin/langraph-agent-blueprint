"""P0 black-box tests for public agent runtime behavior."""

from __future__ import annotations

from langgraph_agent_blueprint.models import AgentRunInput, AgentRunOutput

from .helpers import ai_final, ai_tool_call, assert_final_response_contract, expect_tool_result, expect_user_message


class TestAgentRuntimeBehavior:
    def test_agent_reads_context_and_answers_without_editing(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        readme = temp_project / "README.md"
        readme.write_text("# Demo\n\nSmall LangGraph agent project.\n", encoding="utf-8")

        model = scripted_chat_model(
            steps=[
                expect_user_message("Explain this project."),
                ai_tool_call("read_file", {"path": "README.md"}, call_id="read_readme"),
                expect_tool_result("read_readme", contains="Small LangGraph agent project"),
                ai_final(
                    "This project is a small LangGraph agent project. "
                    "Changed files: none. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: no implementation was requested."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        before = readme.read_text(encoding="utf-8")
        result = runtime.run(
            AgentRunInput(
                message="Explain this project.",
                project_root=str(temp_project),
                mode="default",
            )
        )

        assert isinstance(result, AgentRunOutput)
        assert result.status == "success"
        assert readme.read_text(encoding="utf-8") == before
        assert_final_response_contract(
            result,
            changed_files=[],
            verification_commands=[],
            verification_status="not run",
            remaining_limitations="no implementation was requested",
        )
        model.assert_no_unused_steps()

    def test_agent_completes_simple_tool_calling_loop(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        source = temp_project / "src" / "app.py"
        source.parent.mkdir()
        source.write_text("APP_NAME = 'demo'\n", encoding="utf-8")

        model = scripted_chat_model(
            steps=[
                expect_user_message("Read the application name."),
                ai_tool_call("read_file", {"path": "src/app.py"}, call_id="read_app"),
                expect_tool_result("read_app", contains="APP_NAME"),
                ai_final(
                    "The application name is demo. "
                    "Changed files: none. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: no implementation was requested."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Read the application name.", project_root=str(temp_project)))

        assert result.status == "success"
        assert "demo" in result.final_response
        assert result.error_message is None
        model.assert_no_unused_steps()
