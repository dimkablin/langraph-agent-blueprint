"""P0 black-box tests for edit-and-verify agent behavior."""

from __future__ import annotations

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import (
    ai_final,
    ai_tool_call,
    assert_file_content,
    assert_final_response_contract,
    expect_tool_result,
    expect_user_message,
    scripted_shell,
    shell_error,
    shell_ok,
)


class TestVerificationLoopBehavior:
    def test_agent_runs_verification_after_edit(
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
                expect_user_message("Fix add() and verify it."),
                ai_tool_call("read_file", {"path": "src/math_utils.py"}, call_id="read_source"),
                expect_tool_result("read_source", contains="return a - b"),
                ai_tool_call(
                    "edit_file",
                    {"path": "src/math_utils.py", "old_text": "return a - b", "new_text": "return a + b"},
                    call_id="edit_source",
                ),
                expect_tool_result("edit_source", contains="Edited"),
                ai_tool_call("bash", {"command": "python -m pytest -q"}, call_id="verify_passed"),
                expect_tool_result("verify_passed", contains="1 passed"),
                ai_final(
                    "Changed src/math_utils.py. "
                    "Verification command: python -m pytest -q. "
                    "Verification passed. "
                    "Remaining limitations: none."
                ),
            ]
        )
        shell = scripted_shell({"python -m pytest -q": [shell_ok("1 passed")]})
        runtime = runtime_factory(
            project_root=temp_project,
            chat_model=model,
            permissions=approving_permissions,
            shell_executor=shell,
        )

        result = runtime.run(AgentRunInput(message="Fix add() and verify it.", project_root=str(temp_project)))

        assert result.status == "success"
        assert_file_content(source, "def add(a, b):\n    return a + b\n")
        assert shell.executed_commands == ["python -m pytest -q"]
        assert_final_response_contract(
            result,
            changed_files=["src/math_utils.py"],
            verification_commands=["python -m pytest -q"],
            verification_status="passed",
            remaining_limitations="none",
        )
        model.assert_no_unused_steps()

    def test_agent_fixes_failed_verification_and_reruns_tests(
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
                expect_user_message("Fix add() and verify it."),
                ai_tool_call("read_file", {"path": "src/math_utils.py"}, call_id="read_source"),
                expect_tool_result("read_source", contains="return a - b"),
                ai_tool_call(
                    "edit_file",
                    {
                        "path": "src/math_utils.py",
                        "old_text": "return a - b",
                        "new_text": "return a + b + 1",
                    },
                    call_id="bad_edit",
                ),
                expect_tool_result("bad_edit", contains="Edited"),
                ai_tool_call("bash", {"command": "python -m pytest -q"}, call_id="verify_failed"),
                expect_tool_result("verify_failed", contains="FAILED"),
                ai_tool_call(
                    "edit_file",
                    {
                        "path": "src/math_utils.py",
                        "old_text": "return a + b + 1",
                        "new_text": "return a + b",
                    },
                    call_id="fix_edit",
                ),
                expect_tool_result("fix_edit", contains="Edited"),
                ai_tool_call("bash", {"command": "python -m pytest -q"}, call_id="verify_passed"),
                expect_tool_result("verify_passed", contains="1 passed"),
                ai_final(
                    "Changed src/math_utils.py. "
                    "Verification command: python -m pytest -q. "
                    "Verification passed. "
                    "Remaining limitations: none."
                ),
            ]
        )
        shell = scripted_shell(
            {
                "python -m pytest -q": [
                    shell_error("FAILED tests/test_math_utils.py::test_add"),
                    shell_ok("1 passed"),
                ]
            }
        )
        runtime = runtime_factory(
            project_root=temp_project,
            chat_model=model,
            permissions=approving_permissions,
            shell_executor=shell,
        )

        result = runtime.run(AgentRunInput(message="Fix add() and verify it.", project_root=str(temp_project)))

        assert result.status == "success"
        assert_file_content(source, "def add(a, b):\n    return a + b\n")
        assert shell.executed_commands == ["python -m pytest -q", "python -m pytest -q"]
        assert_final_response_contract(
            result,
            changed_files=["src/math_utils.py"],
            verification_commands=["python -m pytest -q"],
            verification_status="passed",
            remaining_limitations="none",
        )
        model.assert_no_unused_steps()
