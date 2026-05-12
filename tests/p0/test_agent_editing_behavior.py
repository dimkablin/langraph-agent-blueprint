"""P0 black-box tests for agent file editing and writing behavior."""

from __future__ import annotations

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import (
    ai_final,
    ai_tool_call,
    assert_file_content,
    assert_final_response_contract,
    expect_tool_result,
    expect_user_message,
)


class TestAgentEditingBehavior:
    def test_agent_edits_file_and_reports_changed_files(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        source = temp_project / "src" / "math_utils.py"
        source.parent.mkdir()
        source.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Fix add()."),
                ai_tool_call("read_file", {"path": "src/math_utils.py"}, call_id="read_math"),
                expect_tool_result("read_math", contains="return a - b"),
                ai_tool_call(
                    "edit_file",
                    {"path": "src/math_utils.py", "old_text": "return a - b", "new_text": "return a + b"},
                    call_id="edit_math",
                ),
                expect_tool_result("edit_math", contains="Edited"),
                ai_final(
                    "Changed src/math_utils.py to make add() add values. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: verification was not requested."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Fix add().", project_root=str(temp_project)))

        assert result.status == "success"
        assert_file_content(source, "def add(a, b):\n    return a + b\n")
        assert_final_response_contract(
            result,
            changed_files=["src/math_utils.py"],
            verification_commands=[],
            verification_status="not run",
            remaining_limitations="verification was not requested",
        )
        model.assert_no_unused_steps()

    def test_agent_writes_new_file_when_allowed(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        target = temp_project / "src" / "new_module.py"
        model = scripted_chat_model(
            steps=[
                expect_user_message("Create a new module."),
                ai_tool_call(
                    "write_file",
                    {"path": "src/new_module.py", "content": "VALUE = 42\n"},
                    call_id="write_module",
                ),
                expect_tool_result("write_module", contains="Wrote"),
                ai_final(
                    "Changed src/new_module.py by creating the module. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: verification was not requested."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Create a new module.", project_root=str(temp_project)))

        assert result.status == "success"
        assert_file_content(target, "VALUE = 42\n")
        assert_final_response_contract(
            result,
            changed_files=["src/new_module.py"],
            verification_commands=[],
            verification_status="not run",
            remaining_limitations="verification was not requested",
        )
        model.assert_no_unused_steps()

    def test_agent_does_not_overwrite_unrelated_user_changes(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        target = temp_project / "src" / "service.py"
        unrelated = temp_project / "src" / "user_notes.py"
        target.parent.mkdir()
        target.write_text("def enabled():\n    return False\n", encoding="utf-8")
        unrelated.write_text("USER_CHANGE = True\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Enable the service."),
                ai_tool_call("read_file", {"path": "src/service.py"}, call_id="read_service"),
                expect_tool_result("read_service", contains="return False"),
                ai_tool_call(
                    "edit_file",
                    {"path": "src/service.py", "old_text": "return False", "new_text": "return True"},
                    call_id="edit_service",
                ),
                expect_tool_result("edit_service", contains="Edited"),
                ai_final(
                    "Changed src/service.py to enable the service. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: verification was not requested."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Enable the service.", project_root=str(temp_project)))

        assert result.status == "success"
        assert_file_content(target, "def enabled():\n    return True\n")
        assert_file_content(unrelated, "USER_CHANGE = True\n")
        assert result.changed_files == ["src/service.py"]
        model.assert_no_unused_steps()
