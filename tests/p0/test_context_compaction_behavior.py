"""P0 black-box tests for context compaction preserving task outcome."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import (
    ai_final,
    ai_tool_call,
    assert_file_content,
    assert_final_response_contract,
    expect_any_message,
    expect_tool_result,
    expect_user_message,
    scripted_shell,
    shell_ok,
)


class TestContextCompactionBehavior:
    def test_agent_completes_multi_step_task_under_small_context_budget(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        source = temp_project / "src" / "long_module.py"
        source.parent.mkdir()
        source.write_text("# notes\n" + ("context line\n" * 200) + "def flag():\n    return False\n", encoding="utf-8")
        model = scripted_chat_model(
            steps=[
                expect_user_message("Enable flag and verify under a small context budget."),
                ai_tool_call("read_file", {"path": "src/long_module.py"}, call_id="read_long"),
                expect_tool_result("read_long", contains="return False"),
                ai_tool_call(
                    "edit_file",
                    {"path": "src/long_module.py", "old_text": "return False", "new_text": "return True"},
                    call_id="edit_long",
                ),
                expect_tool_result("edit_long", contains="Edited"),
                ai_tool_call("bash", {"command": "python -m pytest -q"}, call_id="verify_long"),
                expect_tool_result("verify_long", contains="1 passed"),
                ai_final(
                    "Changed src/long_module.py. "
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
            config_overrides={"auto_compact_threshold": 50, "max_recent_messages_after_compact": 2},
        )

        result = runtime.run(
            AgentRunInput(
                message="Enable flag and verify under a small context budget.",
                project_root=str(temp_project),
            )
        )

        assert result.status == "success"
        assert result.context_compacted is True
        assert_file_content(source, "# notes\n" + ("context line\n" * 200) + "def flag():\n    return True\n")
        assert_final_response_contract(
            result,
            changed_files=["src/long_module.py"],
            verification_commands=["python -m pytest -q"],
            verification_status="passed",
            remaining_limitations="none",
        )
        model.assert_no_unused_steps()

    def test_agent_compacts_when_model_context_window_would_overflow_below_static_threshold(
        self,
        runtime_factory,
        scripted_chat_model,
        approving_permissions,
        temp_project,
    ):
        session_id = "session_window_overflow"
        old_messages = []
        for index in range(12):
            old_messages.extend(
                [
                    HumanMessage(content=f"old user turn {index} anchor-{index} " + ("x" * 1000)),
                    AIMessage(content=f"old assistant turn {index} decision-{index} " + ("y" * 1000)),
                ]
            )
        model = scripted_chat_model(
            steps=[
                expect_any_message(contains="Compacted prior context:"),
                expect_user_message("Continue with the current task after old context overflow."),
                ai_final("Continued after compaction. Remaining limitations: none."),
            ]
        )
        runtime = runtime_factory(
            project_root=temp_project,
            chat_model=model,
            permissions=approving_permissions,
            config_overrides={
                "context_max_tokens": 8000,
                "auto_compact_threshold": 12000,
                "max_recent_messages_after_compact": 2,
            },
        )
        runtime.dependencies.session_storage.create_session(str(temp_project), session_id, {})
        runtime.dependencies.session_storage.save_messages(str(temp_project), session_id, old_messages)

        result = runtime.run(
            AgentRunInput(
                message="Continue with the current task after old context overflow.",
                project_root=str(temp_project),
                session_id=session_id,
            )
        )

        saved = runtime.dependencies.session_storage.load_session(str(temp_project), session_id)
        assert result.status == "success"
        assert result.context_compacted is True
        assert any(isinstance(message, SystemMessage) and "Compacted prior context:" in str(message.content) for message in saved["messages"])
        model.assert_no_unused_steps()
