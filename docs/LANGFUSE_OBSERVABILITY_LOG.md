# Langfuse Observability Implementation Log

Date: 2026-05-06.

## Implemented

- Added optional Langfuse config and redaction support.
- Added observability Pydantic boundary models.
- Added `ObservabilityService`, `LangfuseCallbackFactory`, `RuntimeEventTraceMapper`, `NoopObservabilityService`, and a future-facing `ObservabilityHook` adapter placeholder.
- Attached callbacks at `AssistantGraphRuntime.invoke`, `resume`, and `stream` while preserving `configurable.thread_id`.
- Mapped selected RuntimeEvents for tools, skills, permissions, hooks, MCP, compaction, session persistence, final responses, and errors.
- Added `/observability` and added Langfuse status to `/doctor`.
- Added optional dependency extra `observability = ["langfuse>=3"]`.
- Added mocked Langfuse tests; no real keys or live Langfuse server are required.

## Manual Smoke Status

Not run in this phase because real Langfuse project keys were not provided. Use the manual smoke in `docs/OBSERVABILITY.md` after creating the Langfuse project.

## Notes

- Langfuse is optional and no-op by default.
- Missing SDK or missing keys are reported as observability status, not runtime failures.
- Secrets are redacted in config/status and event payloads.

## Trace Scoping Fix

Date: 2026-05-06.

Live interactive CLI smoke found that `runtime.*` records were appearing as extra top-level Langfuse traces. The graph callback was scoped, but RuntimeEvents were exported after `app.invoke(...)` through unscoped `client.create_event(...)`.

The runtime now opens one `ObservabilityService.trace_turn(...)` root observation per user turn, creates the LangGraph callback handler inside that active context, records RuntimeEvents before the context closes, and skips RuntimeEvent export when no active trace scope exists. Interactive `lg-agent chat` reuses one session id across prompt turns while still creating one trace per turn.

Default RuntimeEvent mode is `high_signal`: tool/skill/permission/MCP/error/final-response events become child observations, while low-signal lifecycle events are compact `runtime_timeline` metadata.
