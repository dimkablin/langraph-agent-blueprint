# Frontend Event Contract

Audit date: 2026-05-08

## Current Event Envelope

Runtime events use `RuntimeEvent`:

```json
{
  "id": "event_...",
  "type": "tool_call_started",
  "timestamp": "2026-05-08T...",
  "session_id": "session_...",
  "node": null,
  "severity": "info",
  "data": {}
}
```

The Python event type is `EventType` in `models/events.py`. Severity is `info | warning | error`.

Important frontend note: `POST /chat/stream` now returns Server-Sent Events. Each SSE `data:` payload is a `StreamFrame`:

```json
{"type":"event","event":{"id":"event_...","type":"final_response","timestamp":"...","session_id":"session_...","severity":"info","data":{"content":"..."}}}
```

The terminal frame is `{"type":"done","session_id":"...","final_response":"..."}`. Runtime exceptions are emitted as `{"type":"error","error":"..."}` frames.

## Event Taxonomy

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `session_started` | `session_id`, `project_root` | Start timeline/session header | partial | Project path should stay redacted for UI/observability | Low-signal timeline marker |
| `session_persisted` | `session_id` | Persistence indicator | stable | none | Hide by default, show in debug timeline |
| `node_started` | `node` | Debug graph timeline | stable | none | Debug-only |
| `node_finished` | `node` | Debug graph timeline | stable | none | Debug-only |
| `command_started` | `name` | Slash command timeline | stable | command id | Timeline row |
| `command_finished` | `name`, `handled`, optional status | Slash command result | stable | command output ref | Timeline row |
| `model_message` | `content` | Assistant message preview | partial | message id, token usage | Render as assistant draft/final if no separate final response |
| `model_token` | `token` | Token streaming | partial | sequence index, message id | Render only if provider emits token events; keep unknown-safe |
| `final_response` | `content` | Final assistant message | stable | message id | Primary assistant message |
| `error` | error fields from latest error | Error panel | stable enough | normalized error code | Error row/banner |

## Tool Events

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `tool_call_started` | `id`, `name` | Tool activity row | stable | display title, args summary | Show tool started, expandable details if args are available elsewhere |
| `tool_call_finished` | `id`, `name`, `status` | Tool result row | stable | output summary/ref, duration | Show success/error badge and link to result if available |
| `tool_call_error` | `id`, `name`, `status`, `reason` or `error` | Tool failure row | stable | normalized error type | Show warning/error row |
| `mcp_tool_call_started` | `server`, `tool`, call metadata | MCP tool row | partial | standardized `tool_call_id` | Render under MCP section/tool row |
| `mcp_tool_call_finished` | `server`, `tool`, status metadata | MCP result row | partial | output ref | Render as tool result with MCP badge |
| `mcp_tool_call_error` | `server`, `tool`, error metadata | MCP failure | partial | normalized error code | Error row with MCP badge |

## Permission Events

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `permission_required` | `type`, `tool_call_id`, `tool_name`, `action`, `risk`, `args_summary`, `reason`, `args` | Permission modal | stable | explicit `session_id` and `thread_id` inside event data; redaction marker | Blocking modal with action/risk/args summary |
| `permission_resolved` | `tool_call_id`, `tool_name`, `decision`, `reason` | Approval/rejection timeline | stable | user id/source | Timeline row and close modal |

Approval readiness: the modal has enough data for MVP. The API response also returns `session_id` and `thread_id`, which should be kept with modal state. Frontend approval should send `PermissionDecisionDTO(tool_call_id, decision, reason?)`; legacy `{approved}` remains supported only for compatibility.

## Skill, Plugin, Hook Events

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `skill_started` | `name` | Skill activity | stable | skill invocation id | Timeline row with skill badge |
| `skill_finished` | `name`, optional status | Skill result | stable | summary | Timeline row |
| `plugin_loaded` | `name`, `skills_count` | Plugin diagnostics | partial | hooks/tools/MCP/context counts | Low-signal load row or panel status |
| `plugin_skill_registered` | `name` | Plugin diagnostics | stable | plugin name | Debug/panel row |
| `plugin_policy_applied` | contribution/plugin/skill metadata | Skill auto-activation | stable | policy priority | Timeline row with plugin badge |
| `plugin_policy_error` | `error` | Plugin warning | stable | plugin id if available | Warning row |
| `hook_started` | `hook_id`, `hook_point`, plugin metadata | Hook debug | stable | duration | Debug timeline |
| `hook_finished` | `hook_id`, `hook_point` | Hook debug | stable | duration/result action | Debug timeline |
| `hook_event` | `hook_id`, `hook_point`, data | Plugin hook-visible event | stable | event subtype | Timeline/panel row |
| `hook_blocked` | `hook_id`, `hook_point`, `reason` | Blocked prompt/tool info | stable | remediation | Warning row |
| `hook_error` | `hook_id`, `hook_point`, `error` | Hook failure | stable | normalized error code | Warning/error row |

## MCP Discovery Events

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `mcp_server_starting` | `server`, `transport` | MCP panel status | stable | none | Status row |
| `mcp_server_connected` | `server`, `transport`, `pid` | MCP panel status | stable | pid should be hidden by default | Connected badge |
| `mcp_server_failed` | `server`, `error` | MCP diagnostics | stable | retry hint | Warning row |
| `mcp_tools_discovered` | `server`, `count` | MCP panel count | stable | none | Count badge |
| `mcp_resources_discovered` | `server`, `count` | MCP panel count | stable | none | Count badge |
| `mcp_prompts_discovered` | `server`, `count` | MCP panel count | stable | none | Count badge |

## Context Events

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `context_resolution_started` | `count`, `attachments_count` | Context progress | stable | none | Low-signal row |
| `context_fragment_added` | `id`, `kind`, `title`, `trust`, `token_estimate`, `truncated` | Context panel | stable | provider/source id, safe preview ref | Context chip/list item |
| `context_resolution_error` | error dict with message/type/ref data | Context error panel | stable | normalized error code | Warning row tied to ref |
| `context_budget_applied` | `max_tokens`, `used_tokens`, counts/lists | Budget panel | stable | percentage convenience field | Budget meter |

Privacy: context events should not include huge fragment content or full local absolute paths. Existing observability tests cover path redaction for context events; frontend should still treat event data as display metadata, not raw content.

## Subagent Events

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `subagent_started` | `child_run_id`, parent/child ids, name/purpose/status | Child run timeline | stable | display index | Parent timeline row and child-run card |
| `subagent_event` | forwarded child event summary with `child_run_id` | Child progress | partial | original event type/id standardized | Nested timeline row |
| `subagent_finished` | `child_run_id`, status, summary | Child result | stable | result ref | Collapsible child run summary |
| `subagent_error` | `child_run_id` or call id, reason/error | Child failure | stable | normalized error code | Warning/error child card |
| `subagent_timeout` | child ids/status | Timeout | stable | timeout seconds | Warning child card |
| `subagent_cancelled` | child ids/status | Cancelled | stable | cancellation source | Neutral child card |

Known limitation: nested approval/resume for side-effect child runs is not fully implemented. The UI should render the structured subagent error rather than showing an approval modal for an unsupported nested checkpoint.

## Memory, Todo, Compaction, Export

| Event type | Data shape observed | UI use | Stable? | Missing fields | Rendering suggestion |
| --- | --- | --- | --- | --- | --- |
| `memory_updated` | `scope`, `path` or `scopes` | Memory panel refresh | partial | memory item id, path redaction | Low-signal refresh row |
| `compact_started` | `node` | Compaction progress | stable | none | Timeline row |
| `compact_finished` | `summary` | Compaction result | stable | token delta | Timeline row with summary |
| `export_finished` | export metadata | Export result | stable | download URL | Toast/link; `POST /sessions/{id}/export` returns an export record |

There is no dedicated `todo_updated` event in `EventType`; todo changes are represented through tool results/state today.

## Eval Events

No runtime event types currently exist for:

- `eval_started`
- `eval_step_started`
- `eval_step_finished`
- `eval_finished`

Eval/replay is CLI/report-file oriented. A future eval dashboard should add explicit eval API/report contracts rather than mixing eval progress into normal chat events.

## Frontend Event Reducer Recommendations

Create a frontend event layer before building more UI:

```text
frontend/src/runtime/
  types.ts
  events.ts
  reducer.ts
  renderers.ts
```

Rules:

- Keep unknown events renderable through a generic fallback.
- Keep debug/low-signal events collapsible.
- Do not hardcode business decisions in React components.
- Treat event `data` as already redacted but still untrusted display input.
- Store modal state from `permission_required` plus response-level `session_id`/`thread_id`.
- Parse `POST /chat/stream` as SSE `StreamFrame` objects; keep `POST /chat` for non-streaming fallback.

## Contract Gaps

| Gap | Impact | Priority |
| --- | --- | --- |
| TypeScript `StreamFrame`/`RuntimeEventDTO` client types not generated yet | Components would rely on hand-written types | P1 |
| Tool events lack output refs in the event itself | Tool result panel needs to query session/tool calls | P2 |
| Session id/thread id are envelope fields, not always event data | Reducer must combine response metadata with events | P2 |
| Eval events absent | Eval dashboard later needs separate contract | P3 |
