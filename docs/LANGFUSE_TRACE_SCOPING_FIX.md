# Langfuse Trace Scoping Fix

Date: 2026-05-06.

## Baseline Failure

Backend tests did not pass before trace-scoping changes were started, so implementation is paused.

Command:

```powershell
python -m pytest -q
```

Failure:

```text
tests/test_langfuse_config.py::test_langfuse_tracing_environment_alias
AssertionError: assert 'dev' == 'ci'
```

Frontend static tests passed:

```powershell
npm.cmd --prefix frontend run test:static
```

## Root Cause Summary

The project-root `.env` is loaded by `AppConfig.from_env()`. A local `.env` exists and contains both `LANGFUSE_ENVIRONMENT` and `LANGFUSE_TRACING_ENVIRONMENT`. The failing test sets only process `LANGFUSE_TRACING_ENVIRONMENT=ci`, but `AppConfig.from_env()` currently prefers `LANGFUSE_ENVIRONMENT` from `.env` over the process-level tracing alias, so the resolved value remains `dev`.

This is a baseline test isolation/config precedence issue, not the Langfuse trace-scoping bug itself.

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

After baseline is green, the trace-scoping fix should ensure:

- one user turn creates one top-level Langfuse trace
- one interactive CLI chat creates multiple traces grouped by the same Langfuse session id
- runtime events are child observations or compact metadata, not unscoped top-level traces
- project paths are sanitized by default

## Testing Strategy

After baseline is fixed, add tests that simulate active Langfuse trace context and fail when runtime events are emitted with unscoped `create_event(...)`.

## Manual Smoke

Manual smoke remains pending until the implementation proceeds and real Langfuse keys are available.
