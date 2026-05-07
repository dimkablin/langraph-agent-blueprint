# Subagents

Phase 5 replaces the earlier synthetic `AgentService.run_child()` path with a real child graph runtime.

## Runtime Model

The `agent` tool is model-callable, but its normal execution path is graph-routed:

```text
parent model -> ToolCall(name="agent")
-> tool_router reads ToolRuntimeMetadata(route="agent_graph")
-> agent_graph validates SubagentRequest
-> AgentService creates child metadata and isolated child state
-> a child compiled main graph runs with child session/thread ids
-> child result is summarized as a parent ToolMessage
-> parent model continues
```

`AgentTool.run()` intentionally does not fake subagent work when invoked directly through the generic tool executor. Normal assistant workflow must go through `agent_graph`.

## Boundary Models

Subagent DTOs live in `src/langgraph_agent_blueprint/models/subagents.py`:

- `SubagentRequest`
- `ChildRunMetadata`
- `SubagentResult`
- `ResultMergePolicy`

Graph state stores `model_dump(mode="json")` payloads only. Compiled graphs, Langfuse objects, process handles, and mutable parent state are not stored in child-run records.

## Child State Isolation

A child run receives:

- a new validated `child_session_id`
- a new validated `child_thread_id`
- a new `child_run_id`
- parent project root and cwd
- optional copied memory
- optional copied todos
- optional copied resolved context
- a narrowed `allowed_tools_override`
- parent/child linkage metadata

A child run does not share parent `messages`, `pending_tool_calls`, `pending_confirmation`, `tool_results`, `errors`, or mutable `todos` lists unless todos are explicitly copied.

`SubagentRequest.inherit_context` defaults to `true`. Parent context references, resolved fragments, attachment metadata, and budget reports are deep-copied into child state so parent and child do not share mutable containers. Child graphs consume the already-budgeted context fragments through their own `context_builder`; they do not blindly expand large attachments again.

## Tool Scope

`SubagentRequest.allowed_tools` is validated against `ToolRegistry`. If the parent already has an active `allowed_tools_override`, the child scope is intersected with the parent scope so subagents cannot broaden skill or policy limits.

If no explicit child tool list is provided, the runtime defaults to safe read-only tools that do not require permission. Unknown requested tools fail before child execution.

## Permissions

Child tools still enter the normal graph tool route. Read-only child tools can run normally. Side-effect tools such as `write_file`, shell, network, and MCP still require permission.

Nested approval/resume is not fully implemented in Phase 5. If a child graph reaches a permission interrupt, the parent receives a structured subagent error saying that the child side effect requires approval and nested approval is unsupported for that run. The side effect is not executed.

## Events And Streaming

Subagent events are normal `RuntimeEvent` records:

- `subagent_started`
- `subagent_event`
- `subagent_finished`
- `subagent_error`
- `subagent_cancelled`
- `subagent_timeout`

The parent stream includes subagent lifecycle events with `child_run_id`, parent/child session ids, child thread id, name, purpose, status, and summary. Child graph events are forwarded as `subagent_event` summaries so CLI/API can show progress without directly consuming the child checkpoint.

## Persistence

Completed child graph sessions persist through normal `persist_session` under their own child session id. Parent sessions also store sidecar child-run records:

```text
.storage/
  projects/
    {project_hash}/
      sessions/
        {parent_session_id}/
          child_runs/
            {child_run_id}/
              metadata.json
              result.json
              events.jsonl
```

Parent session metadata contains `child_run_refs` so export/replay/frontend work can link parent turns to child transcripts.

## Observability

Langfuse remains an observer. Parent traces record `subagent_started`, `subagent_finished`, and `subagent_error` as high-signal child observations. Forwarded child events are lower-signal runtime timeline data by default.

The child graph is linked with metadata such as `parent_session_id`, `child_session_id`, `child_thread_id`, and `child_run_id`. RuntimeEvent export remains scoped to the active parent turn trace; no unscoped Langfuse event writes are introduced.

## Current Limitations

- Child graph execution is sequential.
- Parallel/background subagents are future work.
- Nested approval/resume for child side-effect tools is guarded but not resumed through the parent yet.
- Timeout is modeled on `SubagentRequest`; hard cancellation of a running child thread/process is future work.
- Task/team/remote-agent lifecycle from the source project is not fully ported yet.
