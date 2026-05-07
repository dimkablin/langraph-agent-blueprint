# Observability

Phase 3 adds optional Langfuse observability as a runtime layer. Langfuse observes graph runs; it does not own workflow routing, tool execution, permissions, hooks, MCP, sessions, or streaming.

## Architecture

The integration has two layers:

1. LangChain/LangGraph callbacks.
   `AssistantGraphRuntime.invoke`, `resume`, and `stream` open one Langfuse root observation per user turn, then attach a Langfuse callback handler through LangGraph config while that observation is active. Existing `configurable.thread_id` is preserved.
2. RuntimeEvent mapping.
   `ObservabilityService` maps selected `RuntimeEvent` records to small, redacted child observations or compact trace metadata for graph-specific lifecycle details that LangChain callbacks do not fully describe.

Key components:

- `LangfuseConfig`
- `TraceContext`
- `TraceMetadata`
- `ObservabilityEvent`
- `ObservabilityService`
- `LangfuseCallbackFactory`
- `RuntimeEventTraceMapper`
- `ObservabilityHook`
- `NoopObservabilityService`

SDK objects stay outside LangGraph state. Graph state remains JSON/checkpointer-safe.

One user turn is one Langfuse trace. An interactive CLI chat produces multiple traces that share one Langfuse `session_id`; each prompt gets its own turn trace, and the shared session id groups them in Langfuse. API approval/resume requests can include `session_id` and pass it to `runtime.resume(...)`, so approval/rejection traces remain grouped with the original chat session instead of falling back to `thread_id`.

## Install

Langfuse is optional:

```powershell
python -m pip install -e ".[observability]"
```

The base CLI still works without Langfuse installed when `LANGFUSE_ENABLED=false`.

## Environment

Supported environment variables:

```env
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=
LANGFUSE_HOST=
LANGFUSE_ENVIRONMENT=dev
LANGFUSE_TRACING_ENVIRONMENT=
LANGFUSE_RELEASE=
LANGFUSE_TRACE_USER_ID=
LANGFUSE_DEBUG=false
LANGFUSE_CAPTURE_INPUTS=true
LANGFUSE_CAPTURE_OUTPUTS=true
LANGFUSE_INCLUDE_PROJECT_PATHS=false
LANGFUSE_RUNTIME_EVENTS_MODE=high_signal
```

Process environment variables override project-root `.env`. Within the same source layer, `LANGFUSE_BASE_URL` is preferred over `LANGFUSE_HOST`, and `LANGFUSE_ENVIRONMENT` is preferred over `LANGFUSE_TRACING_ENVIRONMENT`.

Keys should come from environment or `.env`; do not commit real keys. Project-root `.env` is loaded by `AppConfig.from_env()`, and process environment variables take precedence.

## Disabled And Error Behavior

When Langfuse is disabled:

- no SDK import is required
- no callbacks are attached
- runtime event mapping is a no-op
- graph execution, streaming, tools, skills, hooks, MCP, permissions, and sessions behave normally

When Langfuse is enabled but keys or the SDK are missing:

- normal chat does not crash
- callbacks are omitted
- `/doctor` and `/observability` report `config_error` or `missing_dependency`
- the last trace error is exposed in redacted status

Langfuse network/auth failures are warnings at the observability boundary, not workflow failures.

## Trace Scoping

Trace semantics are turn-scoped:

- one user turn creates one top-level Langfuse trace
- one interactive `lg-agent chat` process creates multiple traces grouped by the same Langfuse `session_id`
- headless `lg-agent query` invocations may each create their own session unless a session id is explicitly supplied
- RuntimeEvents are never emitted through unscoped `client.create_event(...)`

For streaming, the trace context stays open until the returned generator is exhausted. Streamed runtime events are recorded while the same turn trace is active.

## Graph Callback Config

Inside the active turn trace, the graph config includes:

- `callbacks`
- `metadata`
- `tags`
- `run_name`
- existing `configurable.thread_id`

Metadata includes session/thread ids, provider/model, permission mode, environment, release, enabled plugin names when available, MCP server names from config, turn index when available, and a project-root hash. Full local project paths are not sent unless `LANGFUSE_INCLUDE_PROJECT_PATHS=true`.

The callback handler follows the official Langfuse LangChain/LangGraph integration shape: `from langfuse.langchain import CallbackHandler` and passing the handler through graph config callbacks. The handler is created inside the active root observation so LangGraph/LLM/tool observations nest under the turn trace.

## RuntimeEvent Mapping

The default mode is `LANGFUSE_RUNTIME_EVENTS_MODE=high_signal`.

High-signal RuntimeEvents become child observations:

- `tool_call_started`
- `tool_call_finished`
- `tool_call_error`
- `permission_required`
- `permission_resolved`
- `skill_started`
- `skill_finished`
- `hook_blocked`
- `hook_error`
- `mcp_tool_call_started`
- `mcp_tool_call_finished`
- `mcp_tool_call_error`
- `subagent_started`
- `subagent_finished`
- `subagent_error`
- `final_response`
- `error`

Low-signal lifecycle events such as `session_started`, `session_persisted`, normal hook start/finish events, MCP discovery events, forwarded `subagent_event` records, context fragment/budget events, and compaction events are stored as compact `runtime_timeline` metadata by default.

Context resolution errors are high-signal. Context observability payloads include titles, trust markers, token counts, and budget status, not full attachment bodies.

Other modes:

- `all`: record every mapped RuntimeEvent as a child observation
- `metadata_only`: store mapped RuntimeEvents only in compact metadata
- `off`: disable RuntimeEvent export while leaving LangGraph callbacks enabled

LangChain callbacks remain the primary model/tool internal trace path. RuntimeEvent mapping adds graph-specific policy and lifecycle information such as permissions, skills, hooks, MCP, compaction, and persistence without creating separate top-level traces.

## Hooks

Hook lifecycle events are observed through normal RuntimeEvents. Langfuse is not special-cased inside hook business logic, and hooks remain generic graph extension points.

## MCP

MCP server discovery and tool-call events are traced as RuntimeEvents. MCP tool calls still route through `tool_router`, permission flow, `mcp_graph`, and `ToolExecutionService`. Langfuse does not grant MCP tools additional privileges.

## Skills And Tools

Skill and tool events are traced from the same event stream used by CLI/API/frontend:

- `skill_started` / `skill_finished`
- `tool_call_started` / `tool_call_finished` / `tool_call_error`
- permission-required and resolved events for side effects

This includes plugin skills such as `superpowers/brainstorming` and MCP tools such as `mcp.fake.echo`.

## Subagents

Subagent lifecycle events are traced from the same runtime event stream:

- `subagent_started`
- `subagent_finished`
- `subagent_error`
- forwarded child events as compact `subagent_event` timeline records

Child graph metadata includes `parent_session_id`, `child_session_id`, `child_thread_id`, and `child_run_id`. Observability does not run subagents or grant extra permissions; it only records the parent/child lifecycle while the parent turn trace is active.

## Privacy And Redaction

The runtime redacts recursively:

- keys
- tokens
- secrets
- passwords
- authorization/auth fields
- cookies
- API keys

This applies to config/status views, trace metadata, RuntimeEvent data, tool args, MCP header/env-like payloads, and plugin config-like payloads.

Large event payloads are truncated. `LANGFUSE_CAPTURE_INPUTS=false` redacts input-like event payloads. `LANGFUSE_CAPTURE_OUTPUTS=false` redacts output-like event payloads such as final responses and tool outputs while preserving structural event metadata.

`LANGFUSE_INCLUDE_PROJECT_PATHS=false` is the default. Full `project_root`, `cwd`, and private absolute Windows/POSIX paths are replaced with a basename and hash before they enter trace input, output, metadata, child observations, or timeline metadata. Set `LANGFUSE_INCLUDE_PROJECT_PATHS=true` only for local debugging where full paths are acceptable.

External plugin content, MCP resources, MCP prompts, URL context, and pasted attachments are untrusted prompt content. Observability does not change instruction priority: user instructions remain higher priority than plugin methodology, hook-provided context, or attached data.

Context provider content follows the same privacy rules. Full project roots/cwd values are not sent unless `LANGFUSE_INCLUDE_PROJECT_PATHS=true`; large fragment content is not exported in context events.

## Commands

Runtime visibility:

```text
/doctor
/config
/observability
```

`/doctor` includes Langfuse status. `/config` redacts Langfuse keys. `/observability` shows enabled mode, SDK availability, base URL/key presence, capture flags, and last error.

CLI:

```powershell
lg-agent doctor
lg-agent query "/observability"
```

## Manual Smoke

Do not run this without user-provided keys:

```powershell
$env:LANGFUSE_ENABLED = "true"
$env:LANGFUSE_PUBLIC_KEY = "pk-lf-..."
$env:LANGFUSE_SECRET_KEY = "sk-lf-..."
$env:LANGFUSE_BASE_URL = "https://your-langfuse-host"
$env:LANGFUSE_INCLUDE_PROJECT_PATHS = "false"

lg-agent doctor
lg-agent query "hello"
lg-agent query "read README.md using the read_file tool"
```

Expected:

- `doctor` shows Langfuse enabled, SDK installed, keys present, and base URL configured
- a trace appears in the Langfuse UI
- trace metadata includes session id, thread id, provider, model, environment, and release when set
- tool calls and critical runtime events are visible or attached
- no keys, tokens, or authorization values are visible

Interactive chat smoke:

```powershell
lg-agent chat
```

Send:

```text
привет
что ты умеешь?
```

Expected Langfuse UI result:

- exactly two top-level traces
- both traces have the same Langfuse session id
- no `runtime.*` entries appear as separate top-level traces
- runtime events are child observations or compact metadata inside each turn trace
- full `project_root` / `cwd` paths are absent when `LANGFUSE_INCLUDE_PROJECT_PATHS=false`

## Tests

Tests use mocked Langfuse adapters. They do not require real Langfuse keys or a live Langfuse server.

Coverage includes:

- models/config/env loading
- disabled no-op mode
- missing dependency behavior
- graph callback config attachment
- RuntimeEvent mapping
- privacy/redaction/capture flags
- turn-scoped trace grouping and stream context lifetime
- `/doctor`, `/config`, and `/observability`
- graph runs with tools, skills, hooks, permissions, and MCP events

## Troubleshooting

If Langfuse shows many top-level `runtime.*` traces for one chat turn, verify that the runtime is using `ObservabilityService.trace_turn(...)` around graph execution. RuntimeEvent export outside an active trace context is intentionally skipped to avoid unscoped traces.

## Current Limitations

- Live Langfuse smoke is manual and requires user-provided keys.
- The base runtime does not perform an online auth check during tests.
- RuntimeEvent mapping defaults to `high_signal` to avoid duplicating every callback trace.
- Full custom trace-id grouping and richer span hierarchies can be added later if needed.
