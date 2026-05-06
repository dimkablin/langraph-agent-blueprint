# Langfuse Trace Scoping Fix

Date: 2026-05-06.

## Observed Bug

An interactive CLI chat with two prompts:

```text
привет
что ты умеешь?
```

created more than two top-level entries in Langfuse. `runtime.session_started`, `runtime.skill_started`, `runtime.final_response`, and similar RuntimeEvents appeared as separate trace-like rows.

Expected behavior:

- two user turns create two top-level traces
- both traces share one Langfuse session id
- RuntimeEvents are child observations or compact metadata inside the matching turn trace
- full local `project_root` / `cwd` paths are not sent when `LANGFUSE_INCLUDE_PROJECT_PATHS=false`

## Root Cause

The graph run received Langfuse callback config, but after `app.invoke(...)` / stream chunk handling the runtime exported each `RuntimeEvent` through `client.create_event(...)` without an active parent trace context. Langfuse treated those events as independent top-level traces.

The baseline config/env precedence failure was fixed separately in commit `1702fea fix Langfuse env precedence`.

## Baseline Config Fix

`AppConfig.from_env()` now resolves aliases by precedence layer:

```text
explicit AppConfig.from_env(...) overrides
> process environment variables
> project-root .env
> defaults
```

For Langfuse environment specifically:

```text
process LANGFUSE_ENVIRONMENT
> process LANGFUSE_TRACING_ENVIRONMENT
> .env LANGFUSE_ENVIRONMENT
> .env LANGFUSE_TRACING_ENVIRONMENT
> "dev"
```

Within one source layer, `LANGFUSE_ENVIRONMENT` is preferred over `LANGFUSE_TRACING_ENVIRONMENT`. A process-level alias still beats a `.env` preferred key.

## Expected Trace Scoping Fix

The trace-scoping fix ensures:

- one user turn creates one top-level Langfuse trace
- one interactive CLI chat creates multiple traces grouped by the same Langfuse session id
- runtime events are child observations or compact metadata, not unscoped top-level traces
- project paths are sanitized by default

## Files Changed

- `src/langgraph_agent_blueprint/services/observability_service.py`
- `src/langgraph_agent_blueprint/graph/builder.py`
- `src/langgraph_agent_blueprint/cli.py`
- `src/langgraph_agent_blueprint/api/routes_chat.py`
- `src/langgraph_agent_blueprint/config.py`
- `src/langgraph_agent_blueprint/models/observability.py`
- observability tests and docs

## Testing Strategy

Tests use a fake Langfuse client that distinguishes:

- top-level traces
- child observations
- unscoped events
- trace metadata updates

The test suite covers two-turn CLI chat grouping, scoped RuntimeEvent export, callback creation inside the active turn trace, stream context lifetime, path sanitization, disabled/missing dependency behavior, and config redaction.

## Manual Smoke

Manual smoke requires real Langfuse keys:

```powershell
$env:LANGFUSE_ENABLED = "true"
$env:LANGFUSE_PUBLIC_KEY = "pk-lf-..."
$env:LANGFUSE_SECRET_KEY = "sk-lf-..."
$env:LANGFUSE_BASE_URL = "https://your-langfuse-host"
$env:LANGFUSE_INCLUDE_PROJECT_PATHS = "false"

lg-agent chat
```

Send:

```text
привет
что ты умеешь?
```

Expected UI result:

- exactly two top-level traces
- both traces have the same session id
- no top-level `runtime.*` traces
- no full local project path

Live smoke was not run during automated verification because real keys were not provided.

## Remaining Limitations

- The test fake verifies trace scoping but does not prove live Langfuse UI behavior without real keys.
- RuntimeEvent mapping defaults to `high_signal`; richer span taxonomy can be added later without changing graph workflow ownership.
