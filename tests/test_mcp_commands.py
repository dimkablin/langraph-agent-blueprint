"""Slash-command diagnostics for MCP state."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def _runtime(tmp_path: Path) -> AssistantGraphRuntime:
    server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
    deps = build_dependencies(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            llm_provider="fake",
            mcp_config={
                "servers": {
                    "fake": {
                        "enabled": True,
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [str(server)],
                    }
                }
            },
        )
    )
    return AssistantGraphRuntime(deps)


def test_mcp_command_lists_servers_tools_resources_and_prompts(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        overview = runtime.invoke("/mcp", input_kind="headless", project_root=tmp_path)["final_response"]
        tools = runtime.invoke("/mcp tools", input_kind="headless", project_root=tmp_path)["final_response"]
        resources = runtime.invoke("/mcp resources", input_kind="headless", project_root=tmp_path)["final_response"]
        prompts = runtime.invoke("/mcp prompts", input_kind="headless", project_root=tmp_path)["final_response"]
    finally:
        runtime.dependencies.mcp_service.close()

    assert "fake: connected" in overview
    assert "tools: 3" in overview
    assert "mcp.fake.echo" in tools
    assert "mcp://fake/readme" in resources
    assert "summarize" in prompts


def test_doctor_includes_mcp_status(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        result = runtime.invoke("/doctor", input_kind="headless", project_root=tmp_path)
    finally:
        runtime.dependencies.mcp_service.close()

    diagnostics = json.loads(result["final_response"])
    assert diagnostics["mcp"]["servers_total"] == 1
    assert diagnostics["mcp"]["tools_total"] == 3
    assert diagnostics["mcp"]["transport_support"]["stdio"] is True
    assert diagnostics["mcp"]["transport_support"]["streamable_http"] is False


def test_mcp_command_and_doctor_show_invalid_config_entries(tmp_path: Path) -> None:
    deps = build_dependencies(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            llm_provider="fake",
            mcp_config={"servers": {"bad": {"transport": "stdio"}}},
        )
    )
    runtime = AssistantGraphRuntime(deps)

    mcp_output = runtime.invoke("/mcp", input_kind="headless", project_root=tmp_path)["final_response"]
    doctor_output = runtime.invoke("/doctor", input_kind="headless", project_root=tmp_path)["final_response"]

    assert "Invalid MCP servers:" in mcp_output
    assert "bad" in mcp_output
    assert json.loads(doctor_output)["mcp"]["invalid_servers"][0]["name"] == "bad"
