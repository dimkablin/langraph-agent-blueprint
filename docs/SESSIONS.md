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

