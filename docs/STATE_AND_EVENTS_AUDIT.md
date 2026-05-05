# State And Events Audit

## Post-Fix Status (2026-05-06)

State/event overwrites have been fixed for list-like runtime fields:

- `ui_events`
- `tool_results`
- `permission_decisions`
- `errors`
- `tasks`
- `child_runs`
- `artifacts`
- `exported_outputs`

`todos` remains replacement-oriented because `todo_write` owns the visible todo list. `pending_tool_calls` also remains a current-step queue and is explicitly cleared by router/executor nodes.

Events now include:

- `id`
- `type`
- `timestamp`
- `session_id`
- `node`
- `severity`
- `data`

Nodes return event deltas and the reducers append them. Final graph state now preserves command/tool/permission/skill/compact/session/final events for the current run.

Persistence now deduplicates events by event id and writes `session_persisted` as an event. `SessionStorage.create_session` merges metadata instead of overwriting it, so durable fields such as `read_files`, usage, and session metadata survive `append_event` and `append_tool_call`.

Tool result feedback is now provider-compatible:

```text
HumanMessage
AIMessage(tool_calls=[...])
ToolMessage(tool_call_id=...)
AIMessage(final answer)
```

Streaming was changed from "invoke then yield surviving final events" to reading LangGraph value stream deltas.

## Reducers

`AssistantState.messages` is annotated with `add_messages`.

Other list-like fields are plain lists with no reducer:

- `ui_events`
- `tool_results`
- `pending_tool_calls`
- `permission_decisions`
- `todos`
- `tasks`
- `child_runs`
- `artifacts`
- `exported_outputs`
- `errors`

LangGraph therefore treats returned values as replacements. This is the primary reason runtime events disappear.

## Field Writers And Readers

| Field | Writers | Readers | Reducer | Persistence | Finding |
| --- | --- | --- | --- | --- | --- |
| `messages` | `normalize_input`, `model_call`, `skill_router`, `compact_context` | provider, storage, export | `add_messages` | `messages.json` | append works, but no `ToolMessage` is added. |
| `ui_events` | most nodes | CLI/API, `persist_session` | none | `events.jsonl` | overwritten on each node; final state usually has only `final_response`. |
| `pending_tool_calls` | `model_call`, `permission_gate`, `tool_executor` | `tool_router`, `permission_gate`, `tool_executor` | none | no | works as a current-step field. |
| `tool_results` | `tool_router`, `permission_gate`, `tool_executor`, `agent_graph` | `model_call`, `finalize_response`, tests | none | `tool_calls.jsonl` for executor only | overwritten per turn; not returned as ToolMessage. |
| `pending_confirmation` | `tool_router`, `permission_gate` | API/CLI/resume | none | no durable decision except state | interrupt works, but event history is lost after resume. |
| `permission_decisions` | `permission_gate` | tests/storage expected | none | no explicit file | decisions are overwritten/not persisted. |
| `todos` | `tool_executor`, initial state | `/todo`, persistence | none | `todos.json` | saved, but not restored into new graph invocations. |
| `memory` | `context_builder`, memory graph | `/memory`, context builder | none | `memory_refs.json` plus MemoryStorage | load works; remember skill does not write. |
| `usage` | `model_call` | `/cost`, persistence metadata | none | metadata | current invocation only; no aggregate. |
| `errors` | `tool_executor`, `tool_router`, `error_recovery` | routing, final response | none | event only if survives | recoverable errors produce final response, but error events are overwritten. |
| `metadata` | many nodes | routing, commands, persistence | dict replace/merge manually | metadata.json | route flags are stateful; stale flags can affect later paths unless overwritten. |

## Event Lifecycle Observed

Expected events include:

```text
session_started, node_started, node_finished, model_token, model_message,
tool_call_started, tool_call_finished, permission_required, permission_resolved,
skill_started, skill_finished, compact_started, compact_finished,
session_persisted, final_response
```

Actual final `ui_events` in most non-interrupt graph runs:

```text
["final_response"]
```

Actual interrupt result:

```text
["permission_required"]
```

Actual persisted events for a `read_file` session:

```text
events.jsonl: {"type":"node_finished","data":{"node":"compact_decision"}}
```

This proves events are both lost before the client receives them and lost before persistence.

## Nodes That Replace Events

Examples:

- `tool_executor_node` returns `{"ui_events": events}`.
- `persist_session_node` returns `{"ui_events": [session_persisted]}`.
- `finalize_response_node` returns `{"ui_events": [final_response]}`.

Without a reducer, each return replaces previous events.

## Streaming Adapter

`AssistantGraphRuntime.stream()` currently calls `self.invoke(...)` and yields `result.get("ui_events", [])`.

This is not true graph streaming. It cannot emit real-time node/model/tool events because it only sees final state after execution.

## Required State/Event Fixes

P0:

1. Add append reducers for `ui_events`, `tool_results`, `permission_decisions`, `errors`, and likely `child_runs`.
2. Prevent route-only fields from leaking across turns.
3. Add `ToolMessage` construction after tool execution.
4. Preserve `AIMessage.tool_calls` on assistant messages.
5. Make persistence consume the accumulated event stream, not a single overwritten list.
6. Implement true graph streaming adapter using LangGraph stream/astream events or state deltas.
