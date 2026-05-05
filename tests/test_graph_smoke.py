from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime


def test_graph_builds_and_fake_provider_reaches_end(tmp_path):
    config = AppConfig(storage_dir=tmp_path, llm_provider="fake", model_name="fake-model")
    runtime = AssistantGraphRuntime(build_dependencies(config))

    result = runtime.invoke("hello", input_kind="headless")

    assert result["final_response"] == "Fake response: hello"
    assert result["metadata"]["graph_finished"] is True
    assert any(event["type"] == "final_response" for event in result["ui_events"])

