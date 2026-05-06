# MCP Runtime Audit

Audit date: 2026-05-06.

## Pre-Implementation State

- `src/langgraph_agent_blueprint/services/mcp_service.py` is a mock-only registry abstraction. It stores in-process mock handlers and returns them from `discover()`.
- `src/langgraph_agent_blueprint/tools/mcp_tools.py` wraps the mock `MCPToolDefinition` as a `BaseTool`, names it `mcp.<tool>`, and assigns conservative MCP permission metadata.
- `src/langgraph_agent_blueprint/graph/subgraphs/mcp_graph.py` exists, but it only delegates to the generic `tool_executor_node`.
- `dependencies.py` constructs `MCPService(config.mcp_config)` and registers discovered mock tools in `ToolRegistry`.
- `load_registries` exposes `mcp_state` with tools/resources/prompts from `MCPService.discover()`.
- `/mcp` is recognized but currently unsupported by `CommandRegistry`.
- API route `/mcp` returns `mcp_service.discover()`.

## Existing Routing And Permissions

- `tool_router` routes MCP tools by `tool.runtime.route == "mcp_graph"`, not by name prefix.
- Existing MCP adapter metadata uses `ToolRuntimeMetadata(kind="mcp", route="mcp_graph")`.
- Existing MCP permissions are conservative: action `mcp`, risk `high`, `requires_permission=True`, `external=True`.
- Permission flow already runs before `mcp_graph` because `tool_router` asks `PermissionService` for tools that do not route away before permission checks. The current route, however, sends MCP tools to `mcp_graph` before asking permission, so Phase 2 must fix MCP route ordering.

## Mock/Stub Surface

- Mock tools can be registered manually in tests through `MCPService.register_mock_tool(...)`.
- There is no MCP server config model, no stdio process lifecycle, no JSON-RPC transport, no initialize negotiation, no `tools/list`, no `tools/call`, no `resources/list/read`, and no `prompts/list/get`.
- MCP resources and prompts are exposed as empty dictionaries.
- MCP prompts are not registered as skills.

## Current Tests

- Metadata routing tests confirm a custom tool with `route="mcp_graph"` is classified as an MCP route without relying on an `mcp.` prefix.
- Existing graph and permission tests cover generic tool permission behavior.
- No tests start an MCP server, speak JSON-RPC, discover tools/resources/prompts, or call MCP tools through LangGraph.

## Gaps For Phase 2

- Add Pydantic MCP config, connection, contribution, and call/result models.
- Add explicit MCP config loading from `AppConfig.mcp_config`.
- Implement stdio transport lifecycle, JSON-RPC request/response, initialize, discovery, tool call, resource read, and prompt get.
- Register discovered MCP tools in `ToolRegistry` with conservative metadata and graph-owned execution.
- Ensure permission checks happen before MCP tool execution.
- Add MCP runtime events and persistence through existing `ui_events`.
- Add `/mcp` command and `/doctor` MCP diagnostics.
- Add fake stdio MCP server fixture and tests with no live network.

## Post-Implementation Status

Phase 2 replaced the mock-only surface with typed MCP models, explicit config parsing, stdio JSON-RPC transport, initialize/capability negotiation, tools/resources/prompts discovery, MCP tool invocation through LangGraph, `/mcp`, `/doctor` diagnostics, and fake stdio MCP server tests. Streamable HTTP and prompt-to-skill registration remain documented limitations.

## Spec Notes Used

The MCP 2025-11-25 specification defines MCP as JSON-RPC 2.0 with stateful connections and capability negotiation. The stdio transport is newline-delimited JSON-RPC over server stdin/stdout, with stderr reserved for logging. Initialization must be the first interaction and is followed by `notifications/initialized`. Tools are model-controlled, but hosts should keep a human-in-the-loop authorization path for tool invocations.
