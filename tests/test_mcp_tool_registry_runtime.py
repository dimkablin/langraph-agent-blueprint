"""MCP ToolRegistry and graph runtime coverage."""

from __future__ import annotations

import sys
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def _mcp_config() -> dict:
    server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
    return {
        "servers": {
            "fake": {
                "enabled": True,
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(server)],
                "timeout_seconds": 5,
            }
        }
    }


def _runtime(tmp_path: Path) -> AssistantGraphRuntime:
    deps = build_dependencies(
        AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", mcp_config=_mcp_config())
    )
    return AssistantGraphRuntime(deps)


def test_build_dependencies_does_not_discover_or_register_mcp_tools(tmp_path: Path) -> None:
    deps = build_dependencies(
        AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", mcp_config=_mcp_config())
    )

    assert deps.mcp_service.snapshot()["servers"][0]["status"] == "configured"
    assert deps.mcp_service.snapshot()["tools"] == {}
    try:
        deps.tool_registry.get("mcp.fake.echo")
    except KeyError:
        pass
    else:
        raise AssertionError("MCP tools should not be registered during dependency construction")


def test_load_registries_discovers_and_registers_mcp_tools(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        runtime.invoke("hello", input_kind="headless", project_root=tmp_path)
        tool = runtime.dependencies.tool_registry.get("mcp.fake.echo")
    finally:
        runtime.dependencies.mcp_service.close()

    assert tool.metadata()["runtime"]["route"] == "mcp_graph"


def test_mcp_tools_register_with_metadata_driven_route_and_permissions(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        runtime.invoke("hello", input_kind="headless", project_root=tmp_path)
        tool = runtime.dependencies.tool_registry.get("mcp.fake.echo")
        metadata = tool.metadata()

        assert metadata["runtime"]["route"] == "mcp_graph"
        assert metadata["runtime"]["kind"] == "mcp"
        assert metadata["permission"]["action"] == "mcp"
        assert metadata["permission"]["requires_permission"] is True
        assert metadata["permission"]["external"] is True
        assert metadata["input_schema"]["required"] == ["text"]
    finally:
        runtime.dependencies.mcp_service.close()


def test_mcp_tool_call_goes_through_permission_and_returns_tool_message(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        first = runtime.invoke(
            'tool:mcp.fake.echo {"text":"hello"}',
            input_kind="headless",
            project_root=tmp_path,
            thread_id="mcp-echo",
        )
        assert "__interrupt__" in first
        assert first["pending_confirmation"]["tool_name"] == "mcp.fake.echo"
        assert first["pending_confirmation"]["action"] == "mcp"

        result = runtime.resume("mcp-echo", {"approved": True})
    finally:
        runtime.dependencies.mcp_service.close()

    assert result["tool_results"][-1]["status"] == "ok"
    assert "echo: hello" in result["tool_results"][-1]["content"]
    assert result["messages"][-1].type == "ai"
    assert any(event["type"] == "mcp_tool_call_started" for event in result["ui_events"])
    assert any(event["type"] == "mcp_tool_call_finished" for event in result["ui_events"])


def test_mcp_rejection_does_not_call_server(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        first = runtime.invoke(
            'tool:mcp.fake.make_note {"note":"do not write"}',
            input_kind="headless",
            project_root=tmp_path,
            thread_id="mcp-reject",
        )
        result = runtime.resume("mcp-reject", {"approved": False, "reason": "no"})
    finally:
        runtime.dependencies.mcp_service.close()

    assert "__interrupt__" in first
    assert result["tool_results"][-1]["status"] == "rejected"
    assert not any(event["type"] == "mcp_tool_call_started" for event in result["ui_events"])
