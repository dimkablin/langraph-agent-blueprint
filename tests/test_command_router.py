"""Pytest coverage for command router behavior in the Python/LangGraph assistant."""

from langchain_core.messages import HumanMessage

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.nodes.command_router import command_router_node
from langgraph_agent_blueprint.graph.state import create_initial_state


def test_help_routes_locally(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    state = create_initial_state("/help", project_root=tmp_path)
    state["available_commands"] = deps.command_registry.snapshot()

    update = command_router_node(state, deps)

    assert update["command_handled"] is True
    assert "Available commands" in update["final_response"]


def test_prompt_command_continues_to_model(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    state = create_initial_state("/prompt explain this", project_root=tmp_path)
    state["available_commands"] = deps.command_registry.snapshot()

    update = command_router_node(state, deps)

    assert update["command_handled"] is False
    assert update["active_command"]["type"] == "prompt"
    assert isinstance(update["messages"][0], HumanMessage)
    assert "explain this" in update["messages"][0].content


def test_unknown_command_returns_helpful_error(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    state = create_initial_state("/missing", project_root=tmp_path)
    state["available_commands"] = deps.command_registry.snapshot()

    update = command_router_node(state, deps)

    assert update["command_handled"] is True
    assert "Unknown command" in update["final_response"]


def test_context_command_reports_and_clears_context(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    state = create_initial_state("/context clear", project_root=tmp_path)
    state["available_commands"] = deps.command_registry.snapshot()
    state["context_references"] = [{"kind": "file", "value": "README.md", "source": "user_input", "metadata": {}}]
    state["resolved_context"] = [{"id": "ctx_1", "kind": "file", "title": "README.md", "content": "hello", "trust": "trusted_local"}]
    state["metadata"] = {"context_references": state["context_references"], "context_resolved": True}

    update = command_router_node(state, deps)

    assert update["command_handled"] is True
    assert update["context_references"] == []
    assert update["resolved_context"] == []
    assert "context_references" not in update["metadata"]

