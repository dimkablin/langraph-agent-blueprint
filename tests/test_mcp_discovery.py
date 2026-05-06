"""MCP server discovery tests using the fake stdio server."""

from __future__ import annotations

import sys
from pathlib import Path

from langgraph_agent_blueprint.services.mcp_service import MCPService


def _config() -> dict:
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


def test_discovers_tools_resources_prompts_and_events() -> None:
    service = MCPService(_config())
    try:
        discovered = service.discover()
    finally:
        service.close()

    assert discovered["servers"][0]["status"] == "connected"
    assert "mcp.fake.echo" in discovered["tools"]
    assert discovered["tools"]["mcp.fake.echo"]["tool_name"] == "echo"
    assert discovered["resources"]["fake"][0]["uri"] == "mcp://fake/readme"
    assert discovered["prompts"]["fake"][0]["prompt_name"] == "summarize"
    assert any(event["type"] == "mcp_server_connected" for event in discovered["events"])
    assert any(event["type"] == "mcp_tools_discovered" for event in discovered["events"])


def test_http_transport_is_reported_as_unsupported_without_crashing() -> None:
    service = MCPService({"servers": {"remote": {"enabled": True, "transport": "streamable_http", "url": "http://127.0.0.1:9/mcp"}}})

    discovered = service.discover()

    assert discovered["servers"][0]["status"] == "failed"
    assert "streamable_http transport is not implemented" in discovered["servers"][0]["error"]
