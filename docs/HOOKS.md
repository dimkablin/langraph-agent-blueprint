# Hooks

Hooks are graph-owned lifecycle extension points for plugins, observability, policy, skills, tools, MCP, and future frontend integrations.

The runtime intentionally separates responsibilities:

```text
LangGraph node reaches lifecycle point
-> node builds HookContext
-> HookService dispatches registered HookContribution records
-> HookService returns typed HookResult records and hook events
-> graph node applies allowed results through the controlled applier
```

Hooks do not receive mutable graph state and do not execute side effects directly.

## Hook Points

Phase 1 models these hook points:

- `session_start`
- `session_end`
- `user_prompt`
- `pre_context_build`
- `post_context_build`
- `pre_model`
- `post_model`
- `pre_tool`
- `post_tool`
- `permission_request`
- `permission_resolved`
- `pre_skill`
- `post_skill`
- `pre_compact`
- `post_compact`
- `error`

Runtime wiring currently calls the key graph lifecycle points directly from their owning nodes. `session_end` is modeled for registry compatibility, but there is no dedicated process/session shutdown graph node yet.

## Boundary Models

Hook boundary models live in `src/langgraph_agent_blueprint/models/hooks.py`:

- `HookContribution`
- `HookInvocation`
- `HookContext`
- `HookResult`
- `HookPolicy`
- `HookRuntimeMetadata`
- `HookRunSummary`

Graph state stores serialized hook metadata and events. Raw plugin manifest hook entries are validated before entering the registry.

## HookContribution

Core and plugin hooks register metadata like:

```python
HookContribution(
    id="example.add_context",
    plugin_name="example",
    hook_point="pre_model",
    priority=100,
    trusted=False,
    metadata={
        "runtime": {
            "kind": "declarative",
            "action": "add_system_context",
            "content": "Remember to be concise.",
        }
    },
)
```

`HookRegistry` rejects duplicate ids unless an explicit replace is requested, filters by hook point, sorts by priority, supports enable/disable, and exposes snapshots for `/hooks`.

## HookResult

Supported actions are:

- `continue`
- `add_event`
- `add_system_context`
- `modify_context`
- `modify_metadata`
- `block`
- `request_permission`
- `error`

The controlled applier allows only narrow effects:

- `add_system_context` appends a marked hook fragment to metadata and current system context by rebuilding touched nested lists immutably.
- `modify_metadata` stores data under `metadata.hook_metadata[hook_id]`.
- `modify_context` can update whitelisted `context_status` fields only.
- `block` emits `hook_blocked` and gives the graph a final response.
- `request_permission` is not executable in Phase 1; it emits a warning/error event.
- Hook results cannot replace `messages`, `pending_tool_calls`, `tool_results`, permission records, or arbitrary graph fields.

The applier returns state deltas and must not mutate the incoming graph state object; Batch 2 added regression coverage for nested metadata list immutability.

## Plugin Hooks

Plugin manifests may contribute declarative hooks:

```json
{
  "name": "example-plugin",
  "skills": "./skills",
  "hooks": [
    {
      "id": "example.add_pre_model_context",
      "point": "pre_model",
      "action": "add_system_context",
      "content": "Remember to be concise.",
      "priority": 100
    }
  ]
}
```

`PluginService` validates hook entries with Pydantic. Malformed hooks become `hook_warnings` in plugin state instead of crashing discovery. External plugin hooks are untrusted by default and are data-only.

The declarative plugin actions allowed in Phase 1 are:

- `continue`
- `add_event`
- `add_system_context`
- `modify_metadata`
- `block`

Arbitrary Python, JavaScript, shell commands, install hooks, and script fields from plugin repos are not executed.

## Events

Hook lifecycle events are normal `RuntimeEvent` records:

- `hook_started`
- `hook_finished`
- `hook_error`
- `hook_blocked`
- `hook_event`

They are appended to `ui_events`, streamed by `stream-json`, and persisted by `persist_session` with the rest of the session event log.

When Langfuse observability is enabled, hook RuntimeEvents are mapped by `ObservabilityService` like other lifecycle events. Langfuse does not change hook dispatch, trust, result application, or permission behavior.

## Permissions

Hooks cannot bypass `PermissionService`.

If a hook wants a side effect, it must express intent as typed data for a future graph route. Phase 1 does not execute hook-requested side effects. Tool calls created by the model or skill runtime still pass through `tool_router`, metadata-driven permission checks, and LangGraph interrupt/resume.

Hook-added system context is prompt content. Plugin-provided fragments are marked as `[plugin hook: <id>]`, and user instructions remain higher priority than hook or plugin methodology.

## Commands

Use:

```text
/hooks
/hooks list
```

The current command lists registered hooks, hook point, plugin name, priority, and enabled status. `/plugins` also reports plugin hook counts and hook warnings.

## Adding A Hook Point

1. Add the point to `HookPoint`.
2. In the owning graph node, build a `HookContext` through `run_hook_point(...)`.
3. Apply the returned update with the node's normal state update.
4. Add tests for event emission, persistence, and blocked/error behavior.
5. Document whether the point can influence current-turn context or only future state.

## Current Limitations

- `session_end` is modeled but not called by a dedicated shutdown node.
- Declarative plugin hooks are intentionally small and data-only.
- `request_permission` is represented but not wired to create permission interrupts.
- MCP tool calls use the normal `pre_tool`, `permission_request`, `permission_resolved`, `post_tool`, and `error` hook points; hooks still cannot execute MCP calls directly.
- Langfuse observability consumes hook events; it does not introduce Langfuse-specific hook behavior in graph nodes.
- Hook-added context is prompt content and must be treated as untrusted when it comes from external plugins.
