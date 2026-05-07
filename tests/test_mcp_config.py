"""MCP config loading and redaction tests."""

from __future__ import annotations

import sys

from langgraph_agent_blueprint.services.mcp_service import MCPService


def test_loads_stdio_server_config() -> None:
    service = MCPService(
        {
            "servers": {
                "fake": {
                    "enabled": True,
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": ["tests/fixtures/mcp/fake_mcp_server.py"],
                    "trust_level": "untrusted",
                }
            }
        }
    )

    assert [server.name for server in service.server_configs] == ["fake"]
    assert service.enabled_server_configs()[0].stdio is not None


def test_disabled_server_is_not_enabled() -> None:
    service = MCPService({"servers": {"fake": {"enabled": False, "transport": "stdio", "command": sys.executable}}})

    assert service.server_configs[0].enabled is False
    assert service.enabled_server_configs() == []


def test_redacted_config_hides_env_and_header_secrets() -> None:
    service = MCPService(
        {
            "servers": {
                "fake": {
                    "transport": "stdio",
                    "command": sys.executable,
                    "env": {"API_TOKEN": "secret-token", "VISIBLE": "ok"},
                    "headers": {"Authorization": "Bearer secret"},
                }
            }
        }
    )

    redacted = service.redacted_config()["servers"]["fake"]
    assert redacted["stdio"]["env"]["API_TOKEN"] == "***"
    assert redacted["stdio"]["env"]["VISIBLE"] == "ok"
    assert redacted["http"]["headers"]["Authorization"] == "***"


def test_invalid_server_config_is_preserved_in_diagnostics() -> None:
    service = MCPService(
        {
            "servers": {
                "bad": {
                    "transport": "stdio",
                    "env": {"API_TOKEN": "secret-token"},
                }
            }
        }
    )

    diagnostics = service.diagnostics()

    assert diagnostics["invalid_servers"]
    assert diagnostics["invalid_servers"][0]["name"] == "bad"
    assert "stdio" in diagnostics["invalid_servers"][0]["error"]
    assert "secret-token" not in str(diagnostics)
