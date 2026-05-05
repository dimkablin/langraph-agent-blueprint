"""Pytest coverage for resume session behavior in the Python/LangGraph assistant."""

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime


def test_prior_session_can_be_loaded_and_continued(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    runtime = AssistantGraphRuntime(deps)
    first = runtime.invoke("hello", input_kind="headless")

    loaded = deps.session_storage.load_session(first["project_root"], first["session_id"])
    assert loaded["metadata"]["session_id"] == first["session_id"]

    second = runtime.invoke("again", input_kind="headless", session_id=first["session_id"])
    assert second["session_id"] == first["session_id"]
    assert second["final_response"] == "Fake response: again"

