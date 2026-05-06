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

