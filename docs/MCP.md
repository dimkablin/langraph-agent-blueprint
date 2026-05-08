# MCP Client Runtime

MCP support is a graph-owned client integration for explicitly configured external MCP servers. The runtime is a client only; it does not implement MCP server mode.

## Supported Scope

Phase 2 supports:

- stdio MCP server lifecycle
- JSON-RPC initialize and capability negotiation
- `notifications/initialized`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`
- `prompts/list`
- `prompts/get`
- MCP tools registered in `ToolRegistry`
- conservative metadata-driven MCP permissions
- MCP tool execution through LangGraph `mcp_graph`
- MCP lifecycle/tool events in `ui_events`
- `/mcp` status commands and `/doctor` diagnostics

`streamable_http` is modeled in config and diagnostics, but the transport is reported as unsupported in Phase 2. No tests require live network or real external MCP servers.

## Config

MCP servers are explicit runtime config. The service does not auto-discover or silently start random executables.

Example config shape:

```toml
[mcp.servers.filesystem]
enabled = true
transport = "stdio"
command = "python"
args = ["tests/fixtures/mcp/fake_mcp_server.py"]
trust_level = "untrusted"
timeout_seconds = 10
```

The config loader also accepts JSON from `MCP_CONFIG_JSON` or `LG_AGENT_MCP_CONFIG_JSON`:

```powershell
$env:MCP_CONFIG_JSON = '{"servers":{"fake":{"enabled":true,"transport":"stdio","command":"python","args":["tests/fixtures/mcp/fake_mcp_server.py"]}}}'
```

Phase 8 supports project/user TOML config layering and plugin-contributed MCP server configs. Plugin MCP `cwd` values are resolved relative to the plugin root and rejected if they escape that root.

Invalid server entries are preserved as diagnostics instead of being silently skipped. `/mcp` and `/doctor` include `invalid_servers` with redacted validation summaries so config typos remain visible while valid servers continue to work.

## Stdio Transport

`MCPStdioTransport` starts the configured command with `shell=False`, writes newline-delimited JSON-RPC to stdin, reads responses from stdout, captures a short stderr tail, applies timeouts, validates `cwd`, and cleans up the process on close or timeout.

The startup flow is:

```text
initialize
notifications/initialized
tools/list
resources/list
prompts/list
```

Tool, resource, and prompt calls are made later by `MCPService` against the connected transport.

Dependency construction is side-effect-light: `build_dependencies` constructs `MCPService` but does not start configured stdio processes. Discovery happens during explicit graph registry loading (`load_registries`) or explicit diagnostics/status paths such as `/mcp` and `/doctor`, where discovery events and errors can be surfaced in graph state.

## ToolRegistry Integration

Discovered tools register as:

```text
mcp.<server_name>.<tool_name>
```

The route is not inferred from the name. MCP tools expose:

```python
ToolRuntimeMetadata(kind="mcp", route="mcp_graph")
ToolPermissionMetadata(
    action="mcp",
    risk="high",
    requires_permission=True,
    external=True,
)
```

Input schemas come from MCP `inputSchema` and are exposed to providers through normal tool metadata.

## LangGraph Flow

MCP tool calls use the same workflow as other tools:

```text
model_call
-> tool_router
-> permission_gate when required
-> mcp_graph
-> tool_executor
-> model_call
```

Approval routes to `mcp_graph`; rejection appends a rejected `ToolMessage` and does not call the MCP server. `mcp_graph` delegates execution to the same `ToolExecutionService`, so tool results return as `ToolResult` and provider-compatible `ToolMessage`.

## Resources

`resources/list` discovers resources per server. `resources/read` returns `MCPResourceReadResult`:

- `external=True`
- `untrusted=True`
- content truncated by configured output limits
- original payload preserved in `raw`

MCP resources are external context, not local files. The runtime does not mix MCP resource reads with `read_file`.

MCP resources can also be attached as graph context with:

```text
@mcp:<server>:<uri>
```

The context provider calls `MCPService.read_resource`, marks the fragment `mcp_external`, applies the context budget, and renders a prompt-injection warning before the content reaches `context_builder`.

## Prompts

`prompts/list` discovers prompt templates. `prompts/get` returns `MCPPromptGetResult` as untrusted external prompt content.

MCP prompt-to-skill registration is not enabled by default in Phase 2. The documented future namespace is:

```text
mcp/<server_name>/prompt/<prompt_name>
```

## Commands

Slash command visibility:

```text
/mcp
/mcp servers
/mcp tools
/mcp resources
/mcp prompts
```

`/doctor` includes MCP server counts, enabled counts, discovered tool/resource/prompt counts, server statuses, and transport support.
Invalid MCP config entries are shown in both `/mcp` and `/doctor`.

There is no `lg-agent mcp ...` CLI subcommand in Phase 2; use `/mcp` through `lg-agent query` or chat.

## Hooks

MCP tool calls pass through normal hook lifecycle points:

- `pre_tool`
- `permission_request`
- `permission_resolved`
- `post_tool`
- `error` for recoverable tool failures

Hooks still cannot execute MCP calls directly or bypass permissions.

## Observability

When Langfuse is enabled, MCP discovery and tool-call events are exported through the same RuntimeEvent mapping as the rest of the graph. MCP tools still require normal permission approval and route through `mcp_graph`; observability does not execute MCP calls or bypass permission checks.

## Security Model

- MCP servers are external and untrusted unless configured otherwise.
- Server startup is explicit config only.
- Stdio uses `shell=False`.
- Tool calls require permission by default.
- MCP tools cannot bypass `PermissionService`.
- Resource and prompt content is untrusted prompt content.
- Env and header secrets are redacted in diagnostics/config views.
- Timeouts are mandatory.
- Server startup, timeout, unsupported transport, and crash failures produce structured failed state instead of crashing the graph.

Starting a stdio MCP server from config is runtime configuration behavior, not a model-triggered shell call. The model can only request an MCP tool after the server is already configured and discovered, and the tool call still goes through the permission flow.

## Fake Test Server

CI uses a local fixture:

```text
tests/fixtures/mcp/fake_mcp_server.py
```

It implements `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, and `prompts/get` over stdio JSON-RPC. Tests do not require network, GitHub, Langfuse, or real MCP servers.

## Current Limitations

- Streamable HTTP is modeled but not implemented.
- MCP prompt-to-skill registration is documented as future work.
- No MCP server mode.
- No OAuth flow.
- No marketplace or automatic discovery.
- The stdio transport is intentionally synchronous and one-request-at-a-time for Phase 2.
- Langfuse tracing is optional and tested with mocks; live trace visibility requires user-provided Langfuse keys.
