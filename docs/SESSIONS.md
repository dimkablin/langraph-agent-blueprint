# Sessions

Session storage lives under:

```text
.storage/
  projects/
    {project_hash}/
      sessions/
        {session_id}/
          metadata.json
          events.jsonl
          tool_calls.jsonl
          messages.json
          todos.json
          memory_refs.json
          child_runs/
            {child_run_id}/
              metadata.json
              events.jsonl
              result.json
          exports/
          large_outputs/
```

Implemented:

- create session
- append events
- append tool calls
- save/load messages
- list sessions
- clear session
- rewind stored messages
- export transcript through `ExportService`

Resume loads stored metadata/messages and can continue with the same `session_id`.

Runtime status after fixes:

- Session metadata is merged instead of overwritten by event/tool append operations.
- Stored messages preserve `AIMessage.tool_calls` and `ToolMessage.tool_call_id`.
- Todos, memory refs, usage, and durable read history metadata are restored for later turns.
- `/resume <session_id>` restores state inside the graph command route.
- `/export` creates transcript files and records `exported_outputs`.
- Real subagent runs use child session ids for their own transcript and store parent-linked sidecar records under `child_runs/{child_run_id}`. Parent session metadata records `child_run_refs`.
