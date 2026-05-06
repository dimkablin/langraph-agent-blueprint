"""Pytest coverage for permission interrupts behavior in the Python/LangGraph assistant."""

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_graph_interrupts_for_approval_and_resumes_after_approve(tmp_path):
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )
    first = runtime.invoke("tool:write_file created.txt hello", input_kind="headless", thread_id="approval-test", project_root=tmp_path)

    assert "__interrupt__" in first
    assert first["pending_confirmation"]["tool_name"] == "write_file"

    resumed = runtime.resume("approval-test", {"approved": True})

    assert resumed["permission_decisions"][0]["approved"] is True
    assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "hello"
