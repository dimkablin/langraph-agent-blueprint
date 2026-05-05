# MCP

`MCPService` is an architectural abstraction for MCP server configuration, discovery, tools, resources, prompts, and MCP-derived skills.

Current implementation:

- safe disabled-by-default behavior when no config exists
- mock tool registration for tests
- internal `MCPToolAdapter` that wraps discovered MCP tools as `BaseTool`
- state exposure through `mcp_state`

Limitations:

- external MCP process startup and OAuth flows are not implemented yet
- MCP prompt-to-skill conversion is represented architecturally, not fully implemented
- MCP tools require conservative permission defaults

The graph smoke tests do not require MCP configuration.

