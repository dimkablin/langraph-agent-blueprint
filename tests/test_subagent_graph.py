"""Pytest coverage for subagent graph behavior in the Python/LangGraph assistant."""

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.subgraphs.agent_graph import build_agent_graph
from langgraph_agent_blueprint.graph.state import create_initial_state


def test_child_graph_runs_and_result_merges(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    app = build_agent_graph(deps).compile()
    state = create_initial_state("delegate", project_root=tmp_path)
    state["pending_tool_calls"] = [{"id": "1", "name": "agent", "args": {"prompt": "inspect"}}]

    result = app.invoke(state)

    assert result["child_runs"][0]["status"] == "completed"
    assert "inspect" in result["child_runs"][0]["result"]

