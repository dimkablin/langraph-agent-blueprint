"""P0 black-box tests for session persistence through public runtime contracts."""

from __future__ import annotations

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import ai_final, ai_tool_call, expect_tool_result, expect_user_message


class TestSessionPersistenceBehavior:
    def test_session_resume_preserves_todo_state_through_public_runtime(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        model = scripted_chat_model(
            steps=[
                expect_user_message("Track the verification task."),
                ai_tool_call(
                    "todo_write",
                    {"todos": [{"content": "Run verification", "status": "pending"}]},
                    call_id="todo_task",
                ),
                expect_tool_result("todo_task", contains="Updated 1 todos"),
                ai_final(
                    "Tracked the verification task. "
                    "Changed files: none. "
                    "Verification command: not run. "
                    "Verification status: not run. "
                    "Remaining limitations: task is still pending."
                ),
            ]
        )
        runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)
        session_id = "session-p0-persistence"

        first = runtime.run(
            AgentRunInput(
                message="Track the verification task.",
                project_root=str(temp_project),
                session_id=session_id,
            )
        )
        resumed = runtime.run(
            AgentRunInput(
                message="/todo",
                project_root=str(temp_project),
                session_id=session_id,
            )
        )

        assert first.status == "success"
        assert first.session_id == session_id
        assert resumed.status == "success"
        assert resumed.session_id == session_id
        assert any(todo.get("content") == "Run verification" for todo in resumed.todos)
        assert "Run verification" in resumed.final_response
        model.assert_no_unused_steps()
