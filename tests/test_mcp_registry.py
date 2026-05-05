"""Pytest coverage for mcp registry behavior in the Python/LangGraph assistant."""

from claude_code_langgraph.services.mcp_service import MCPService
from claude_code_langgraph.tools.mcp_tools import MCPToolAdapter


def test_no_mcp_config_does_not_crash():
    service = MCPService(config={})

    assert service.discover() == {"tools": {}, "resources": {}, "prompts": {}}


def test_mocked_mcp_tool_can_register():
    service = MCPService(config={})
    service.register_mock_tool("mock.echo", lambda data: {"echo": data})
    discovered = service.discover()

    adapter = MCPToolAdapter(discovered["tools"]["mock.echo"])
    assert adapter.name == "mcp.mock.echo"

