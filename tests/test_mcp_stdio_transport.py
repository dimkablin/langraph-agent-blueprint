"""Stdio JSON-RPC transport coverage for local MCP servers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from langgraph_agent_blueprint.models.mcp import MCPServerConfig, MCPStdioConfig
from langgraph_agent_blueprint.services.mcp_transport import MCPStdioTransport, MCPTransportError


def _server_config(*extra_args: str, timeout_seconds: float = 5.0) -> MCPServerConfig:
    server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
    return MCPServerConfig(
        name="fake",
        transport="stdio",
        stdio=MCPStdioConfig(command=sys.executable, args=[str(server), *extra_args]),
        timeout_seconds=timeout_seconds,
    )


def test_stdio_transport_initialize_and_cleanup() -> None:
    transport = MCPStdioTransport(_server_config())
    try:
        transport.start()
        response = transport.request("initialize", {"protocolVersion": "2025-11-25"})
        transport.notify("notifications/initialized")

        assert response["capabilities"]["tools"] == {}
        assert transport.state.status == "connected"
        assert transport.state.pid is not None
    finally:
        transport.close()

    assert transport.state.status == "stopped"


def test_stdio_transport_timeout_cleans_up() -> None:
    transport = MCPStdioTransport(_server_config("--hang-initialize", timeout_seconds=0.2))
    try:
        transport.start()
        with pytest.raises(MCPTransportError, match="timed out"):
            transport.request("initialize", {"protocolVersion": "2025-11-25"})
    finally:
        transport.close()

    assert transport.state.status == "stopped"


def test_stdio_transport_rejects_invalid_cwd() -> None:
    config = _server_config()
    assert config.stdio is not None
    bad_config = config.model_copy(update={"stdio": config.stdio.model_copy(update={"cwd": "does-not-exist"})})
    transport = MCPStdioTransport(bad_config)

    with pytest.raises(MCPTransportError, match="cwd does not exist"):
        transport.start()
