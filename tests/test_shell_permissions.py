from langgraph.types import Command

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime


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

