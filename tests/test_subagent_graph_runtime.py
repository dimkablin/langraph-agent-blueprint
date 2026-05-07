"""Runtime tests for real child graph execution behind the agent tool."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import ToolMessage

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.graph.state import create_initial_state
from langgraph_agent_blueprint.models.subagents import SubagentRequest


def _runtime(tmp_path: Path) -> AssistantGraphRuntime:
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    return AssistantGraphRuntime(deps)


def test_child_state_is_isolated_and_allowed_tools_do_not_broaden_parent_scope(tmp_path: Path) -> None:
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    parent = create_initial_state("parent", project_root=tmp_path)
    parent["metadata"] = {"allowed_tools_override": ["read_file"], "subagent_depth": 0}
    parent["messages"] = []
    parent["todos"] = [{"content": "parent todo"}]
    request = SubagentRequest(prompt="hello", allowed_tools=["read_file", "write_file"], inherit_todos=False)

    metadata = deps.agent_service.create_child_metadata(parent, request)
    child_state = deps.agent_service.create_child_state(parent, request, metadata, deps.tool_registry)

    assert child_state["metadata"]["allowed_tools_override"] == ["read_file"]
    child_state["metadata"]["parent_session_id"] == parent["session_id"]
    assert child_state["session_id"] != parent["session_id"]
    assert child_state["thread_id"] != parent["thread_id"]
    assert child_state["messages"] is not parent["messages"]
    assert child_state["todos"] == []


def test_agent_tool_launches_child_graph_and_returns_tool_message(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("subagent read payload", encoding="utf-8")
    runtime = _runtime(tmp_path)
    prompt = json.dumps(
        {
            "prompt": 'tool:read_file {"path":"notes.txt"}',
            "name": "reader",
            "purpose": "Read a file through a child graph",
            "allowed_tools": ["read_file"],
            "max_turns": 4,
        }
    )

    result = runtime.invoke(f"tool:agent {prompt}", input_kind="headless", project_root=tmp_path)

    child = result["child_runs"][-1]
    assert child["metadata"]["status"] == "completed"
    assert child["result"]["status"] == "ok"
    assert "subagent read payload" in child["result"]["summary"]
    assert any(isinstance(message, ToolMessage) and message.tool_call_id for message in result["messages"])
    assert result["tool_results"][-1]["name"] == "agent"
    assert result["tool_results"][-1]["status"] == "ok"
    event_types = [event["type"] for event in result["ui_events"]]
    assert "subagent_started" in event_types
    assert "subagent_event" in event_types
    assert "subagent_finished" in event_types


def test_child_graph_persists_child_run_and_parent_reference(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    prompt = json.dumps({"prompt": "hello from child", "name": "summarizer"})

    result = runtime.invoke(f"tool:agent {prompt}", input_kind="headless", project_root=tmp_path)
    child = result["child_runs"][-1]
    child_run_id = child["metadata"]["child_run_id"]
    child_session_id = child["metadata"]["child_session_id"]
    parent_session_id = result["session_id"]

    parent = runtime.dependencies.session_storage.load_session(tmp_path, parent_session_id)
    child_session = runtime.dependencies.session_storage.load_session(tmp_path, child_session_id)
    child_dir = runtime.dependencies.session_storage.child_run_dir(tmp_path, parent_session_id, child_run_id)

    assert child_run_id in parent["metadata"]["child_run_refs"]
    assert child_session["messages"]
    assert (child_dir / "metadata.json").exists()
    assert (child_dir / "result.json").exists()

