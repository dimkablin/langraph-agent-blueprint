from __future__ import annotations

import pytest
from langchain_core.messages import ToolMessage

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime
from claude_code_langgraph.graph.nodes.tool_router import tool_router_node
from claude_code_langgraph.graph.state import create_initial_state


def _runtime(tmp_path):
    return AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )


@pytest.mark.parametrize("skill", ["batch", "debug", "simplify", "skillify", "stuck", "update-config", "verify"])
def test_builtin_skill_explicit_invocation_uses_skill_runtime_events(tmp_path, skill):
    result = _runtime(tmp_path).invoke(f"/skill {skill} test args", input_kind="headless", project_root=tmp_path)
    event_types = [event["type"] for event in result["ui_events"]]

    assert "skill_started" in event_types
    assert "skill_finished" in event_types
    assert result["active_skill"]["name"] == skill
    assert result["metadata"]["allowed_tools_override"] == result["active_skill"]["result"]["allowed_tools"]


def test_skill_tool_invocation_reaches_skill_graph_and_adds_tool_message(tmp_path):
    result = _runtime(tmp_path).invoke('tool:skill {"skill":"debug","args":"failure"}', input_kind="headless", project_root=tmp_path)

    assert result["active_skill"]["name"] == "debug"
    assert any(isinstance(message, ToolMessage) for message in result["messages"])
    assert any(event["type"] == "skill_started" for event in result["ui_events"])


def test_disallowed_tool_inside_skill_scope_is_rejected(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    state = create_initial_state("call", project_root=tmp_path)
    state["metadata"] = {"allowed_tools_override": ["read_file"]}
    state["pending_tool_calls"] = [{"id": "call_1", "name": "write_file", "args": {"path": "x.txt", "content": "x"}}]

    update = tool_router_node(state, deps)

    assert update["tool_results"][0]["status"] == "rejected"
    assert update["tool_results"][0]["metadata"]["reason"] == "disallowed_by_skill"
