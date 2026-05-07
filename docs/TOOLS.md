# Tools

Tools implement `BaseTool` with:

- name
- description
- Pydantic input/output schemas
- `ToolPermissionMetadata`
- `ToolRuntimeMetadata`
- sync/async run methods
- timeout/output limit metadata

Core tools:

- `read_file`
- `write_file`
- `edit_file`
- `notebook_read`
- `notebook_edit`
- `glob`
- `grep`
- `bash`
- `powershell`
- `web_fetch`
- `web_search`
- `todo_write`
- `agent`
- `skill`
- `diagnostics`
- `mcp.<server>.<tool>` adapters discovered from configured MCP servers

Tool workflow is graph-owned: UI/API call the graph, the graph routes to permission and execution nodes, and services perform low-level operations.

When Langfuse observability is enabled, tool lifecycle RuntimeEvents are mapped to redacted observability events after graph execution or during streaming. This does not change tool routing or permissions.

Tool names are identity only: registry key, provider function name, display/logging/persistence id, and skill `allowed_tools` matching. Semantic behavior comes from metadata:

- `tool.permission.action`
- `tool.permission.risk`
- `tool.permission.is_read_only`
- `tool.permission.requires_permission`
- `tool.permission.allowed_in_plan_mode`
- `tool.permission.requires_network`
- `tool.runtime.kind`
- `tool.runtime.route`
- `tool.runtime.state_effects`

At the runtime boundary, provider-specific tool calls are normalized into `ToolCall` DTOs and tool execution returns `ToolResult` DTOs. The graph stores serialized DTO payloads in state and converts results to `ToolMessage` through one shared converter.

`ToolExecutionContext` is a read-only/minimal DTO. Tools receive project/cwd paths, session/thread ids, read-file history, and frozen metadata snapshots; they do not receive the mutable whole LangGraph state. Tool behavior that needs to affect state must return metadata-declared `ToolStateEffect` records.

Post-execution graph state changes are represented as typed `ToolStateEffect` records. Built-in effects include file-read history, todo replacement, and child-run append. `ToolExecutionService` applies these effects by effect kind, not by `tool.name`.

To add a new side-effecting tool, declare metadata on the tool class:

```python
class MyWriteTool(BaseTool[MyInput, MyOutput]):
    name = "my_write_tool"
    permission = ToolPermissionMetadata(
        action="write",
        risk="medium",
        requires_permission=True,
        reason="This tool modifies files.",
    )
    runtime = ToolRuntimeMetadata(
        kind="custom",
        route="execute",
        state_effects=["record_file_write"],
    )
```

Runtime status after fixes:

- Provider tool schemas are bound to supported models with registry names preserved.
- Tool results are returned as `ToolMessage` and then routed back to `model_call`.
- File/search/shell/notebook/todo tools have end-to-end fake-provider tests.
- `edit_file` replaces an exact snippet only when it appears exactly once. Missing snippets and multi-match snippets fail without changing the file.
- Ollama `qwen3:14b` was manually verified for native `read_file` tool calling.
- `web_fetch` is disabled unless network is enabled and approved; when enabled it returns untrusted-content warning metadata, allows only absolute `http`/`https` URLs, blocks private/internal hosts by default, caps response bytes, validates redirect final URLs, and summarizes binary content.
- `web_search` reports unavailable when no provider is configured.
- Tool routing for skill, agent, and MCP tools is metadata-driven through `tool.runtime.route`.
- The `agent` tool routes to `agent_graph` and executes a real child graph with isolated child state. Direct `AgentTool.run()` execution is not the normal workflow path and returns a graph-route error instead of synthetic work.
- MCP tools are discovered through `MCPService`, registered with `ToolRuntimeMetadata(kind="mcp", route="mcp_graph")`, and require approval by default through `ToolPermissionMetadata(action="mcp", risk="high", external=True)`.
- MCP adapter input schemas come from server `tools/list` `inputSchema` payloads; tool calls return through the normal `ToolResult` -> `ToolMessage` loop.
- Observability redacts secret-like tool args before export and respects `LANGFUSE_CAPTURE_INPUTS` / `LANGFUSE_CAPTURE_OUTPUTS`.

## Context References Are Not Tool Bypasses

`@file`, `@directory`, `@glob`, `@notebook`, `@mcp`, `@url`, and text attachments are resolved by the graph context provider layer before `context_builder`. They do not execute arbitrary tools directly from CLI/API. URL context uses the same `WebService` guardrails as `web_fetch`, and MCP resource context uses `MCPService` resource reads with external trust markers. Side-effecting tools still require normal permission approval.
