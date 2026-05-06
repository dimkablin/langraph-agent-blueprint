# Hooks Runtime Audit

Audit date: 2026-05-06.

## Current State

- `src/langgraph_agent_blueprint/services/hook_service.py` exists, but it is a minimal string-key dispatcher. It stores callables under arbitrary names, runs them with a raw payload, and emits only `hook_finished` / `hook_error` events.
- `src/langgraph_agent_blueprint/graph/nodes/hook_runner.py` calls `HookService.run("post_turn", ...)` after the model/tool loop has no more tool calls. That is the only active hook invocation point.
- `AssistantState` already has `hooks_state`, but it is only used for a `last_hook_count` counter.
- `RuntimeEvent` already validates `hook_finished` and `hook_error`, but does not yet include `hook_started` or `hook_blocked`.
- Plugin manifests have a loose `hooks` placeholder in `models/schemas.py`, but production plugin discovery does not validate or expose hook contributions.
- `PluginService` returns `"hooks": []` in plugin state and does not register declarative hooks.

## Existing Hook-Related Classes

- `HookService`: minimal raw dispatcher with no typed hook points, no contribution metadata, no typed results, and no controlled state applier.
- `hooks_state`: graph state field reserved for hook runtime data.
- `hook_runner_node`: single post-turn graph node that invokes the raw hook dispatcher.

There is no `HookContribution`, `HookInvocation`, `HookContext`, `HookResult`, `HookPolicy`, `HookRuntimeMetadata`, or `HookRegistry` model/registry layer yet.

## Current Hook Calls

Only one call exists:

```text
tool_router(no_tools) -> hook_runner -> HookService.run("post_turn", {"session_id": ..., "state": ...})
```

No hooks are called during user prompt normalization, context building, model calls, tool routing/execution, permission request/resolution, skill invocation, compaction, or error recovery.

## Missing Hook Points

Required Phase 1 hook points are missing at runtime:

- `session_start`
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

`session_end` has no natural process boundary in the current graph yet, so it should be modeled and documented as a limitation.

## Plugin Hook Gaps

- External plugin discovery can load skills and bootstrap fragments, but not hooks.
- Plugin hook entries are not parsed with Pydantic validation.
- Malformed hook entries cannot produce structured hook warnings.
- `/plugins` does not show hook counts or hook warnings.
- There is no declarative hook schema and no protection boundary for plugin-provided hook content beyond the current absence of execution.

## Test Coverage Gaps

Existing tests cover events, permissions, tools, skills, commands, sessions, plugin skills, and Superpowers policy. Hook-specific tests are absent for:

- hook model validation
- registry priority/duplicates/enablement
- HookService typed invocation and error isolation
- controlled HookResult application
- graph lifecycle hook points
- plugin declarative hook discovery
- hook event persistence
- hook security constraints

## Phase 1 Implementation Gaps

This phase should add a typed hooks layer where LangGraph remains workflow owner:

```text
graph node reaches lifecycle point
-> node builds typed hook context
-> HookService invokes matching registered contributions
-> HookService returns typed HookResult records and hook events
-> graph node applies allowed HookResult effects through a controlled applier
```

The implementation should keep plugin hooks declarative/data-only, avoid arbitrary plugin scripts, preserve `PermissionService` as the side-effect gate, and keep hook-added context clearly marked as plugin-provided prompt content.
