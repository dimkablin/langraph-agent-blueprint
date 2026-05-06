"""Pytest coverage for graph smoke behavior in the Python/LangGraph assistant."""

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_graph_builds_and_fake_provider_reaches_end(tmp_path):
    config = AppConfig(storage_dir=tmp_path, llm_provider="fake", model_name="fake-model")
    runtime = AssistantGraphRuntime(build_dependencies(config))

    result = runtime.invoke("hello", input_kind="headless")

    assert result["final_response"] == "Fake response: hello"
    assert result["metadata"]["graph_finished"] is True
    assert any(event["type"] == "final_response" for event in result["ui_events"])

