# Permissions

`PermissionService` classifies tool calls and returns `allow`, `ask`, or `deny`.

Modes:

- `default`
- `accept_edits`
- `bypass_read_only`
- `plan`
- `strict`

Policy:

- read-only file/search tools can run in default mode
- write/edit tools require approval unless policy allows
- shell tools require approval
- network tools require approval and config enablement
- MCP/plugin tools default conservative
- plan mode blocks side effects until approval

Human approval uses LangGraph interrupt/resume. `pending_confirmation` is stored in graph state before `permission_gate` interrupts.

