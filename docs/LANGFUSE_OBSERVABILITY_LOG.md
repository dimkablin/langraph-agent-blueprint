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
