# State and Events Audit

Current acceptance status as of 2026-05-06.

## State Reducers

`AssistantState.messages` uses LangGraph `add_messages`. List-like runtime history fields use append reducers where deltas must survive between nodes:

- `ui_events`
- `tool_results`
- `permission_decisions`
- `errors`
- `artifacts`
- `exported_outputs`
- `child_runs`
- `tasks`

`todos` intentionally does not blindly append because `todo_write` replaces or updates the visible todo list. `pending_tool_calls` is also managed as the current-step queue and is cleared by tool execution or policy rejection.

## Event Lifecycle

Events are serialized dictionaries with:

- `id`
- `type`
- `timestamp`
- `session_id` when available
- `node` when applicable
- `severity` when applicable
- `data`

The current runtime emits and preserves:

- `session_started`
- `node_started`
- `node_finished`
- `model_token`
- `model_message`
- `tool_call_started`
- `tool_call_finished`
- `tool_call_error`
- `permission_required`
- `permission_resolved`
- `skill_started`
- `skill_finished`
- `command_started`
- `command_finished`
- `compact_started`
- `compact_finished`
- `memory_updated`
- `session_persisted`
- `final_response`
- `error`

## Acceptance Evidence

| Scenario | Event evidence |
| --- | --- |
| `/help` | stream-json emitted `session_started`, `command_started`, `command_finished`, `session_persisted`, `final_response`. |
| `read_file` | final state included `tool_call_started`, `tool_call_finished`, `session_persisted`, `final_response`. |
| `write_file` approval | interrupted with `permission_required`; resume emitted `permission_resolved` and `tool_call_finished`. |
| `/skill remember` | emitted `skill_started`, `memory_updated`, `skill_finished`. |
| `/compact` | emitted `compact_finished` and updated `context_status.compacted=True`. |
| stream-json | produced multiple JSONL records, not a single final object; final event was `final_response`. |

## Persistence

Session storage writes:

- `metadata.json`
- `events.jsonl`
- `messages.json`
- `tool_calls.jsonl`
- `todos.json`
- `memory_refs.json`
- export files under storage `exports/`

Acceptance workspace evidence showed these files under:

```text
test_runs/final-acceptance-workspace/.storage_acceptance2/projects/{project_hash}/sessions/{session_id}/
```

## Historical Audit Result

The pre-fix audit found that events and tool results were overwritten between nodes. Current reducers and acceptance evidence replace that historical result.
