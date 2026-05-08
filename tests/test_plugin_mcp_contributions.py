"""Plugin MCP server contribution tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.services.plugin_service import PluginService


def test_plugin_mcp_config_merges_and_discovers_explicitly(tmp_path: Path) -> None:
    plugin = tmp_path / "example_plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    fake_server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
    manifest = {
        "name": "example_plugin",
        "mcp_servers": {
            "fake": {
                "enabled": True,
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(fake_server)],
                "cwd": ".",
            }
        },
    }
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    service = PluginService([plugin], storage_dir=tmp_path / "storage")
    discovered = service.discover()
    assert discovered["mcp"]

    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, plugin_paths=[plugin]))
    runtime = AssistantGraphRuntime(deps)
    try:
        result = runtime.invoke("/mcp tools", input_kind="headless", project_root=tmp_path)
    finally:
        deps.mcp_service.close()

    assert "mcp.example_plugin.fake.echo" in deps.tool_registry.snapshot()
    assert "mcp.example_plugin.fake.echo" in result["final_response"]


def test_plugin_mcp_cwd_escape_is_reported_as_warning(tmp_path: Path) -> None:
    plugin = tmp_path / "bad_plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"bad_plugin","mcp_servers":{"bad":{"transport":"stdio","command":"python","cwd":"../escape"}}}',
        encoding="utf-8",
    )

    state = PluginService([plugin], storage_dir=tmp_path / "storage").discover()

    assert state["mcp"] == []
    assert any("path traversal" in warning["error"] for warning in state["mcp_warnings"])
