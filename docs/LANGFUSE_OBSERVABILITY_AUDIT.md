# Langfuse Observability Audit

Audit date: 2026-05-06.

## Existing Observability Surface

- Runtime events are typed as `RuntimeEvent` and appended to `ui_events`.
- `persist_session` writes all accumulated `ui_events` to session storage.
- CLI/API streaming reads graph `ui_events`; it does not call tools or services directly.
- Hooks emit `hook_started`, `hook_finished`, `hook_error`, and `hook_blocked`.
- MCP discovery/tool calls emit `mcp_server_*`, `mcp_*_discovered`, and `mcp_tool_call_*`.
- Permission flow emits `permission_required` and `permission_resolved`.
- Skills, model calls, tool calls, compaction, persistence, and final responses already have runtime events.

## Graph Invocation Points

- `AssistantGraphRuntime.invoke(...)` creates initial state and calls `self.app.invoke(state, config)`.
- `AssistantGraphRuntime.resume(...)` calls `self.app.invoke(Command(resume=...), config)`.
- `AssistantGraphRuntime.stream(...)` calls `self.app.stream(state, config, stream_mode="values")`.
- CLI, API, and frontend routes all go through `AssistantGraphRuntime`.

These are the correct places to attach Langfuse callbacks. Langfuse should not be called by CLI/API directly for workflow.

## Callback Integration

The current graph config only sets:

```python
{"configurable": {"thread_id": state["thread_id"]}}
```

Langfuse can be added by preserving that key and adding:

- `callbacks`
- `metadata`
- `tags`
- `run_name`

Official Langfuse docs for the current Python SDK use `from langfuse.langchain import CallbackHandler` and pass the handler through LangChain/LangGraph config.

## RuntimeEvent Mapping

The runtime already has the semantic events Langfuse callbacks do not know about:

- permissions
- skills
- hooks
- MCP lifecycle/calls
- plugin policy
- compaction
- session persistence
- recovered errors

These can be mapped centrally after graph invocation/stream chunks by an `ObservabilityService`. The mapper should create compact, redacted event payloads and avoid sending huge message/tool payloads.

## Data That Must Not Be Sent

- Langfuse secret key or public key
- OpenAI/Anthropic/API provider keys
- authorization headers
- tokens/passwords/secrets in config, MCP env/header values, plugin config, or tool args
- full local paths unless explicitly enabled later
- large model/tool/resource payloads beyond truncation limits

## Tests Needed

- Langfuse config/env validation and redaction.
- Disabled mode is no-op and does not import Langfuse.
- Enabled mode with missing SDK reports structured status and does not crash.
- Mocked SDK callback creation and graph config callback attachment.
- RuntimeEvent mapping for tool, skill, permission, hook, MCP, final response, and error events.
- Privacy tests for config secrets, tool args, and capture-input/output flags.
- `/doctor`, `/config`, and optional `/observability` command coverage.
- Regression coverage for hooks, MCP, Superpowers, stream-json, and metadata-driven permissions through the full suite.

## Limitations For Phase 3

- Tests use mocked Langfuse adapters and do not verify live trace visibility.
- Manual live smoke requires user-provided Langfuse project keys.
- RuntimeEvent mapping should be lightweight; LangChain callbacks remain the primary model/tool trace integration.
- Full trace grouping with custom trace IDs can be added later if needed.
