# Permissions

`PermissionService` is policy-only: it reads the resolved tool's `ToolPermissionMetadata` and returns `allow`, `ask`, or `deny`. Tool names are not used to infer action, risk, plan-mode behavior, shell/network/write status, or external-tool safety.

Modes:

- `default`
- `accept_edits`
- `bypass_read_only`
- `plan`
- `strict`

Policy:

- tools with `permission.is_read_only=True` can run in default mode
- tools with `permission.requires_permission=True` ask for approval unless a mode explicitly allows that action
- `accept_edits` allows `write`/`edit` actions only; it does not allow shell or network actions
- network tools declare `permission.requires_network=True`, still require approval, and also depend on network config
- MCP/plugin/custom tools default conservative when adapters do not provide safer metadata
- plan mode blocks non-read-only side effects unless `permission.allowed_in_plan_mode=True`

Human approval uses LangGraph interrupt/resume. `pending_confirmation` is stored in graph state before `permission_gate` interrupts.

## Hooks

Hooks cannot bypass permission policy. Plugin hooks are declarative/data-only and cannot execute shell, write files, use network, or call MCP directly.

Hook results that add system context are treated as prompt content only. Tool calls that arise after that context still pass through `tool_router`, metadata-driven `PermissionService`, and LangGraph interrupt/resume. Phase 1 models `request_permission` as a hook result action, but the controlled applier emits an unsupported warning instead of creating a permission interrupt.

Runtime status after fixes:

- `permission_required` and `permission_resolved` events survive to CLI/API/frontend responses.
- Decisions append to `permission_decisions` and persist with session events.
- Rejected tool calls append a structured `ToolMessage` so the model can explain the rejection.
- Network tools with `requires_permission=True` are no longer auto-allowed just because they are read-only.
- `permission_required` action/risk values come from tool metadata, not registry names.
- Confirmation args are recursively redacted with default secret-like keys plus each tool's `sensitive_arg_keys`.

## MCP

MCP tools are external by default. Discovered MCP tools register conservative metadata:

```python
ToolPermissionMetadata(
    action="mcp",
    risk="high",
    requires_permission=True,
    external=True,
)
```

`tool_router` checks `PermissionService` before routing an MCP call to `mcp_graph`. Approval resumes to `mcp_graph`; rejection appends a rejected `ToolMessage` and does not call the MCP server. MCP resource and prompt content is marked external/untrusted and cannot directly create side effects.
