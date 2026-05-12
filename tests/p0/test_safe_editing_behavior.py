"""P0 black-box tests for safe editing snapshots and rollback."""

from __future__ import annotations

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import (
    ai_final,
    ai_tool_call,
    assert_file_content,
    expect_tool_result,
    expect_user_message,
    scripted_shell,
    shell_error,
)


class TestSafeEditingBehavior:
    def test_snapshot_is_created_before_edit(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        source_file = temp_project / "src" / "settings.py"
        source_file.parent.mkdir()
        source_file.write_text("VALUE = 'old'\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Update the setting safely."),
                ai_tool_call("read_file", {"path": "src/settings.py"}, call_id="read_settings"),
                expect_tool_result("read_settings", contains="VALUE = 'old'"),
                ai_tool_call(
                    "edit_file",
                    {
                        "path": "src/settings.py",
                        "old_text": "VALUE = 'old'",
                        "new_text": "VALUE = 'new'",
                    },
                    call_id="edit_settings",
                ),
                expect_tool_result("edit_settings", contains="Edited"),
                ai_final(
                    "Changed src/settings.py. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: not verified."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

        result = runtime.run(AgentRunInput(message="Update the setting safely.", project_root=str(temp_project)))

        model.assert_no_unused_steps()
        assert result.status == "success"
        assert_file_content(source_file, "VALUE = 'new'\n")
        assert result.changed_files == ["src/settings.py"]
        assert result.rollback_available is True
        assert len(result.snapshots) == 1
        snapshot = result.snapshots[0]
        assert snapshot.path == "src/settings.py"
        assert snapshot.existed is True
        stored_snapshot = runtime.dependencies.session_storage.load_file_snapshot(
            temp_project,
            result.session_id,
            snapshot.snapshot_id,
        )
        assert stored_snapshot["content"] == "VALUE = 'old'\n"

    def test_rollback_restores_previous_file_content(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        source_file = temp_project / "src" / "settings.py"
        source_file.parent.mkdir()
        source_file.write_text("VALUE = 'old'\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Update the setting safely."),
                ai_tool_call("read_file", {"path": "src/settings.py"}, call_id="read_settings"),
                expect_tool_result("read_settings", contains="VALUE = 'old'"),
                ai_tool_call(
                    "edit_file",
                    {
                        "path": "src/settings.py",
                        "old_text": "VALUE = 'old'",
                        "new_text": "VALUE = 'new'",
                    },
                    call_id="edit_settings",
                ),
                expect_tool_result("edit_settings", contains="Edited"),
                ai_final(
                    "Changed src/settings.py. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: not verified."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)
        edit_result = runtime.run(AgentRunInput(message="Update the setting safely.", project_root=str(temp_project)))

        rollback_result = runtime.run(
            AgentRunInput(
                message="Rollback the last file change.",
                project_root=str(temp_project),
                session_id=edit_result.session_id,
                action="rollback",
            )
        )

        model.assert_no_unused_steps()
        assert rollback_result.status == "success"
        assert_file_content(source_file, "VALUE = 'old'\n")
        assert rollback_result.rollback_result is not None
        assert rollback_result.rollback_result.status == "restored"
        assert rollback_result.rollback_result.path == "src/settings.py"
        assert "Rollback restored src/settings.py" in rollback_result.final_response

    def test_failed_verification_preserves_snapshot_for_recovery(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        source_file = temp_project / "src" / "math_utils.py"
        source_file.parent.mkdir()
        source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Break add() and verify it."),
                ai_tool_call("read_file", {"path": "src/math_utils.py"}, call_id="read_math"),
                expect_tool_result("read_math", contains="return a + b"),
                ai_tool_call(
                    "edit_file",
                    {
                        "path": "src/math_utils.py",
                        "old_text": "return a + b",
                        "new_text": "return a - b",
                    },
                    call_id="edit_math",
                ),
                expect_tool_result("edit_math", contains="Edited"),
                ai_tool_call("bash", {"command": "python -m pytest -q"}, call_id="verify_failed"),
                expect_tool_result("verify_failed", contains="FAILED"),
                ai_final(
                    "Changed src/math_utils.py. "
                    "Verification command: python -m pytest -q. "
                    "Verification failed. "
                    "Remaining limitations: rollback is available from the saved snapshot."
                ),
            ]
        )
        shell = scripted_shell({"python -m pytest -q": [shell_error("FAILED tests/test_math_utils.py::test_add")]})
        runtime = runtime_factory(
            project_root=temp_project,
            chat_model=model,
            permissions=approving_permissions,
            shell_executor=shell,
        )

        result = runtime.run(AgentRunInput(message="Break add() and verify it.", project_root=str(temp_project)))

        model.assert_no_unused_steps()
        assert result.status == "success"
        assert result.verification_status == "failed"
        assert result.rollback_available is True
        assert len(result.snapshots) == 1
        stored_snapshot = runtime.dependencies.session_storage.load_file_snapshot(
            temp_project,
            result.session_id,
            result.snapshots[0].snapshot_id,
        )
        assert stored_snapshot["content"] == "def add(a, b):\n    return a + b\n"
