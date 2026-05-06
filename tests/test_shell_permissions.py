"""Pytest coverage for shell permissions behavior in the Python/LangGraph assistant."""

from langgraph.types import Command

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_shell_command_creates_pending_confirmation(tmp_path):
    runtime = AssistantGraphRuntime(build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake")))

    result = runtime.invoke("tool:bash echo hi", input_kind="headless", thread_id="shell-test")

    assert "__interrupt__" in result
    assert result["pending_confirmation"]["tool_name"] == "bash"


def test_shell_rejection_blocks_execution(tmp_path):
    runtime = AssistantGraphRuntime(build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake")))
    runtime.invoke("tool:bash echo hi", input_kind="headless", thread_id="shell-reject")

    result = runtime.resume("shell-reject", {"approved": False, "reason": "no"})

    assert result["tool_results"][0]["status"] == "rejected"
    assert "rejected" in result["final_response"].lower()

