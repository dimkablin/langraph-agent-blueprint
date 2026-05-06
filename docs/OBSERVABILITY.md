# Observability

Phase 3 adds optional Langfuse observability as a runtime layer. Langfuse observes graph runs; it does not own workflow routing, tool execution, permissions, hooks, MCP, sessions, or streaming.

## Architecture

The integration has two layers:

1. LangChain/LangGraph callbacks.
   `AssistantGraphRuntime.invoke`, `resume`, and `stream` attach a Langfuse callback handler through LangGraph config. Existing `configurable.thread_id` is preserved.
2. RuntimeEvent mapping.
   `ObservabilityService` maps selected `RuntimeEvent` records to small, redacted Langfuse events for graph-specific lifecycle details that LangChain callbacks do not fully describe.

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
```

`LANGFUSE_BASE_URL` is preferred. `LANGFUSE_HOST` is accepted as a compatibility alias. `LANGFUSE_ENVIRONMENT` is preferred over `LANGFUSE_TRACING_ENVIRONMENT`.

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

## Graph Callback Config

The graph config includes:

- `callbacks`
- `metadata`
- `tags`
- `run_name`
- existing `configurable.thread_id`

Metadata includes session/thread ids, provider/model, permission mode, environment, release, enabled plugin names when available, MCP server names from config, and a project-root hash. Full local project paths are not sent unless `LANGFUSE_INCLUDE_PROJECT_PATHS=true`.

The callback handler follows the official Langfuse LangChain/LangGraph integration shape: `from langfuse.langchain import CallbackHandler` and passing the handler through graph config callbacks.

## RuntimeEvent Mapping

The mapper records compact semantic events for:

- `session_started`
- `command_started`
- `command_finished`
- `model_message`
- `tool_call_started`
- `tool_call_finished`
- `tool_call_error`
- `permission_required`
- `permission_resolved`
- `skill_started`
- `skill_finished`
- `hook_started`
- `hook_finished`
- `hook_blocked`
- `hook_error`
- `mcp_server_connected`
- `mcp_tools_discovered`
- `mcp_tool_call_started`
- `mcp_tool_call_finished`
- `mcp_tool_call_error`
- `compact_started`
- `compact_finished`
- `session_persisted`
- `final_response`
- `error`

LangChain callbacks remain the primary model/tool internal trace path. RuntimeEvent mapping adds graph-specific policy and lifecycle information such as permissions, skills, hooks, MCP, compaction, and persistence.

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

External plugin content, MCP resources, and MCP prompts are untrusted prompt content. Observability does not change instruction priority: user instructions remain higher priority than plugin methodology or hook-provided context.

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

## Tests

Tests use mocked Langfuse adapters. They do not require real Langfuse keys or a live Langfuse server.

Coverage includes:

- models/config/env loading
- disabled no-op mode
- missing dependency behavior
- graph callback config attachment
- RuntimeEvent mapping
- privacy/redaction/capture flags
- `/doctor`, `/config`, and `/observability`
- graph runs with tools, skills, hooks, permissions, and MCP events

## Current Limitations

- Live Langfuse smoke is manual and requires user-provided keys.
- The base runtime does not perform an online auth check during tests.
- RuntimeEvent mapping is intentionally lightweight to avoid duplicating every callback trace.
- Full custom trace-id grouping and richer span hierarchies can be added later if needed.
