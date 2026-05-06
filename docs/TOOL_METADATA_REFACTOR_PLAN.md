# Tool Metadata Refactor Plan

This plan follows `docs/TOOL_NAME_SEMANTICS_AUDIT.md`. It was originally written before implementation; the current status is tracked below and the original ordered plan is retained for traceability.

## Implementation Status

Implemented on 2026-05-06:

- Added `ToolPermissionMetadata`, `ToolRuntimeMetadata`, and `ToolStateEffect` in `src/claude_code_langgraph/models/tool_metadata.py`.
- Added `permission` and `runtime` metadata to `BaseTool`, with backward-compatible `safety`, `is_read_only`, and `requires_permission` properties.
- Added explicit permission/runtime metadata for all core tools.
- Reworked `PermissionService` to be policy-only and metadata-driven.
- Reworked confirmation payloads to use tool metadata and redact sensitive args recursively.
- Reworked `tool_router` to route via `tool.runtime.route`.
- Reworked post-tool state updates to use typed state effects instead of `tool.name`.
- Kept fake-provider shorthand aliases as documented test ergonomics; generic `tool:<name> <json>` remains the recommended deterministic path.

## Target Design

Tool metadata is the source of permission, safety, runtime-kind, routing, and state-effect classification.

Tool name remains valid only for:

- registry lookup key
- display/logging/persistence identity
- provider schema name
- allowed-tools matching
- examples/tests/docs

Consumers should not infer semantics from names.

## New/Updated Models

Add metadata models near tool/runtime boundary models, likely `src/claude_code_langgraph/models/tool_metadata.py` or `src/claude_code_langgraph/tools/base.py`.

```python
class ToolPermissionMetadata(FrozenRuntimeModel):
    action: PermissionAction
    risk: PermissionRisk
    is_read_only: bool = False
    requires_permission: bool = False
    reason: str | None = None
    allowed_in_plan_mode: bool = False
    requires_network: bool = False
    external: bool = False
    sensitive_arg_keys: set[str] = Field(default_factory=set)
```

Recommended runtime metadata:

```python
ToolKind = Literal[
    "file",
    "search",
    "shell",
    "network",
    "notebook",
    "todo",
    "skill",
    "agent",
    "diagnostics",
    "mcp",
    "plugin",
    "custom",
]

class ToolRuntimeMetadata(FrozenRuntimeModel):
    kind: ToolKind
    route: Literal["execute", "skill_graph", "agent_graph", "mcp_graph"] = "execute"
    supports_streaming: bool = False
    returns_large_output: bool = False
    can_run_in_skill: bool = True
    can_run_in_headless: bool = True
    state_effects: list[Literal["todos", "read_history", "child_runs", "metadata"]] = Field(default_factory=list)
```

If this feels too heavy, `ToolPermissionMetadata` plus a small `runtime_kind`/`route` field may be enough.

## Required Tool Metadata Table

Initial values should be explicit on each built-in tool class or supplied by a registry adapter.

| Tool | action | risk | is_read_only | requires_permission | allowed_in_plan_mode | requires_network | external | runtime kind | route | state effects |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `read_file` | read | low | true | false | true | false | false | file | execute | read_history |
| `write_file` | write | medium | false | true | false | false | false | file | execute | read_history/metadata |
| `edit_file` | edit | medium | false | true | false | false | false | file | execute | read_history/metadata |
| `notebook_read` | read | low | true | false | true | false | false | notebook | execute | none |
| `notebook_edit` | edit | medium | false | true | false | false | false | notebook | execute | none |
| `glob` | read | low | true | false | true | false | false | search | execute | none |
| `grep` | read | low | true | false | true | false | false | search | execute | none |
| `bash` | shell | high | false | true | false | false | false | shell | execute | none |
| `powershell` | shell | high | false | true | false | false | false | shell | execute | none |
| `web_fetch` | network | medium | false | true | false | true | false | network | execute | none |
| `web_search` | network | medium | false | true | false | true | false | network | execute | none |
| `todo_write` | todo | low | false | false | true | false | false | todo | execute | replace_todos |
| `skill` | skill | low | false | false | true | false | false | skill | skill_graph | none |
| `agent` | agent | medium | false | false | true | false | false | agent | agent_graph | append_child_run |
| `diagnostics` | read | low | true | false | true | false | false | diagnostics | execute | none |
| `mcp.*` | mcp | high | false | true | false | false | true | mcp | mcp_graph | adapter-declared |
| plugin/custom tools | unknown/plugin by default | high by default | false by default | true by default | false by default | adapter-declared | true by default | plugin/custom | execute unless declared | adapter-declared |

## Ordered Fixes

| Priority | Area | Files | Change | Tests | Risk |
| --- | --- | --- | --- | --- | --- |
| P0 | Tool metadata model | `tools/base.py`, new model module | Add `permission` and `runtime` metadata with backward-compatible derivation from current fields. | Metadata model serialization tests. | Medium: touches central tool metadata. |
| P0 | Permission policy | `services/permission_service.py` | Remove `_permission_action` and `_permission_risk`; `decide` and `confirmation_payload` consume `tool.permission`. Change `confirmation_payload` signature to include resolved tool. | Custom tool action/risk tests; MCP/plugin conservative default tests; existing permission E2E. | High: security path. |
| P0 | Read-history state effects | `services/tool_execution_service.py`, file tools | Replace `tool.name in {"read_file",...}` with declared `state_effects` or output-provided state update protocol. | Custom file-like read/edit test; edit prior-read regression. | High: edit safety. |
| P1 | Tool routing | `graph/nodes/tool_router.py` | Replace `skill`/`agent`/`mcp.` hardcoded routing with `tool.runtime.route`/`kind`. Unknown external tools default to execute only after conservative permission. | Custom skill-like/agent-like/MCP adapter tests. | Medium. |
| P1 | State effect merge | `services/tool_execution_service.py` | Replace `todo_write` and `agent` name checks with `state_effects` or standard `state_update` from output. | Custom todo-like and agent-like tests. | Medium. |
| P1 | Diagnostics | `services/diagnostics_service.py`, command docs | Report tools grouped by permission/runtime metadata completeness. | `/doctor` asserts metadata completeness and flags missing metadata. | Low/medium. |
| P2 | Fake provider | `services/model_provider.py`, tests | Keep generic `tool:<name> <json>` contract; move `bash`/`write_file`/`agent` shorthands to fixtures or document them as aliases. | Fake provider tests updated to generic JSON. | Low. |
| P2 | Tests/docs | `tests/test_command_permission_models.py`, docs | Replace assertions that encode name-derived action/risk with metadata-driven tests. | Full pytest. | Low. |
| P2 | Skill runtime review | `graph/nodes/skill_router.py`, skill metadata | Evaluate whether direct-memory behavior should be skill metadata rather than `remember` name. | Custom memory-like skill test if implemented. | Medium, outside tool-name scope. |

## Acceptance Criteria

- [x] No production permission action/risk is derived from `tool.name` or `tool_call.name`.
- [x] `PermissionService` reads `ToolPermissionMetadata`.
- [x] `permission_required` includes action/risk from metadata.
- [x] Plan mode uses `permission.allowed_in_plan_mode`.
- [x] Network checks use `permission.requires_network` and config.
- [x] `tool_router` routes special tool categories by runtime metadata, not name or prefix.
- [x] MCP/plugin/custom tools receive conservative metadata by default where adapters provide or lack metadata.
- [x] `tool_execution_service` merges state effects through tool metadata/hook output, not tool names.
- [x] Existing built-in tools preserve current behavior.
- [x] Tests include custom tools for metadata-driven behavior:
  - write/medium permission
  - shell/high permission
  - network requires config
  - skill route
  - agent route
  - read-history state effect
  - todo state effect
- [ ] `/doctor` can be expanded further to report metadata completeness by group; core metadata is already exposed through registry snapshots.
- [x] Full `python -m pytest -q` passes after final verification.

## Migration Notes

Keep current `BaseTool.safety`, `is_read_only`, and `requires_permission` temporarily as compatibility fields. Introduce the new metadata and make `BaseTool.metadata()` expose both legacy and new fields during the migration. After tests and docs are updated, callers should stop using legacy fields directly.
