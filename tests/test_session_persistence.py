"""Pytest coverage for session persistence behavior in the Python/LangGraph assistant."""

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_events_and_tool_calls_are_written(tmp_path):
    runtime = AssistantGraphRuntime(build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake")))

    result = runtime.invoke("hello", input_kind="headless")
    session_dir = runtime.dependencies.session_storage.session_dir(result["project_root"], result["session_id"])

    assert (session_dir / "metadata.json").exists()
    assert (session_dir / "events.jsonl").exists()
    assert (session_dir / "tool_calls.jsonl").exists()


def test_reused_thread_does_not_duplicate_hydrated_session_messages(tmp_path):
    runtime = AssistantGraphRuntime(
        build_dependencies(
            AppConfig(
                storage_dir=tmp_path / "storage",
                project_root=tmp_path,
                cwd=tmp_path,
                llm_provider="fake",
                auto_compact_threshold=100_000,
            )
        )
    )
    session_id = None
    message_counts = []

    for index in range(3):
        result = runtime.invoke(
            f"turn {index}",
            input_kind="headless",
            session_id=session_id,
            thread_id="same-thread",
            project_root=tmp_path,
        )
        session_id = result["session_id"]
        message_counts.append(len(result["messages"]))

    assert message_counts == [2, 4, 6]

    persisted = runtime.dependencies.session_storage.load_session(tmp_path, session_id)
    assert len(persisted["messages"]) == 6

