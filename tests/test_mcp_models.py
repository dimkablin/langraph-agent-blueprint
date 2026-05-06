"""Typed boundary coverage for MCP runtime models."""

from __future__ import annotations

import sys

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.models.mcp import (
    MCPConnectionState,
    MCPServerConfig,
    MCPStdioConfig,
    MCPToolContribution,
)


def test_stdio_server_config_validates() -> None:
    config = MCPServerConfig(
        name="fake",
        transport="stdio",
        stdio=MCPStdioConfig(command=sys.executable, args=["tests/fixtures/mcp/fake_mcp_server.py"]),
    )

    assert config.name == "fake"
    assert config.transport == "stdio"
    assert config.stdio is not None


def test_invalid_stdio_config_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MCPServerConfig(name="fake", transport="stdio")


def test_connection_state_serializes() -> None:
    state = MCPConnectionState(name="fake", status="connected", transport="stdio", capabilities={"tools": {}})

    assert state.model_dump(mode="json") == {
        "name": "fake",
        "status": "connected",
        "transport": "stdio",
        "capabilities": {"tools": {}},
        "error": None,
        "pid": None,
    }


def test_tool_contribution_uses_registry_name() -> None:
    contribution = MCPToolContribution(
        server_name="fake",
        tool_name="echo",
        registry_name="mcp.fake.echo",
        input_schema={"type": "object"},
    )

    assert contribution.registry_name == "mcp.fake.echo"
    assert contribution.server_name == "fake"
