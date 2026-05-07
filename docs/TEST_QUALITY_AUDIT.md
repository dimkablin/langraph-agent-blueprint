# Test Quality Audit

Date: 2026-05-07

## Baseline

- `python -m pytest -q`: passed.
- `npm.cmd --prefix frontend run test:static`: passed.
- Test suite contains unit, boundary, graph runtime, runtime audit, frontend contract, MCP fake-server, hooks, Superpowers, and observability fake-client tests.

## Strengths

- Regression tests exist for provider tool binding, ToolMessage feedback, metadata-driven permissions/routes/state effects, event reducers, session persistence, Superpowers bootstrap/trigger, hooks, MCP stdio, and Langfuse trace scoping.
- MCP tests use a local fake stdio server and do not require live network.
- Langfuse tests use a fake client that distinguishes top-level traces, child observations, and unscoped events.
- `.env` precedence tests now isolate temp `.env` files and process env.
- Frontend static tests check API contract direction: frontend calls graph-facing backend endpoints only.

## Findings

### P1: No Regression Test For Session Identifier Path Traversal

- Area: `SessionStorage`, API chat/session routes.
- Evidence: searches found many session-id tests but none for `../`, `..\\`, absolute paths, or path separators.
- Why it matters: `session_id` is user-controllable through API schemas and storage uses it as a path segment.
- Suggested test: `SessionStorage.session_dir/create_session/load_session` rejects IDs containing separators, `..`, drive prefixes, reserved names, and empty strings. API schemas should reject them too.

### P1: No Test For Ambiguous `edit_file` Match

- Area: file tools.
- Evidence: tests cover prior-read requirement and happy path, but not multiple `old_text` matches.
- Why it matters: Ambiguous edits are a common coding-assistant failure mode.
- Suggested test: file with `old_text` appearing twice returns structured error and does not modify the file.

### P1: No Test For Invalid MCP Config Diagnostics

- Area: MCP config.
- Evidence: invalid config test checks model rejection, but service parser silently skips invalid server entries.
- Why it matters: `/doctor` should tell users about invalid configured servers.
- Suggested test: malformed server config appears in diagnostics with a structured warning.

### P1: No Test Proving MCP Discovery Is Lazy Or Explicit

- Area: dependency construction and MCP lifecycle.
- Evidence: `build_dependencies` calls `mcp_service.discover()` immediately.
- Why it matters: Tests prove discovery works, but not when process startup is allowed to happen.
- Suggested test: dependency construction with configured MCP does not start process until load/registry phase if architecture is changed.

### P1: Web Fetch Lacks Security/Size Tests

- Area: network tools.
- Evidence: existing runtime audit covers disabled mode and local HTTP happy path.
- Missing cases: scheme restrictions, localhost/private-network policy if desired, redirect policy, very large bodies, binary content, timeout.
- Suggested test: large response is bounded before materializing too much data; unsupported schemes fail before network call.

### P1: Tool Context Mutability Is Not Tested

- Area: tools and state effects.
- Evidence: tests verify state effects but do not assert tools cannot mutate input state through `ToolExecutionContext.state`.
- Suggested test: malicious test tool mutates `context.state`; graph state should not reflect it unless a typed `ToolStateEffect` is returned.

### P2: Observability API Resume Session Grouping Is Not Covered

- Area: FastAPI approval route and `AssistantGraphRuntime.resume`.
- Evidence: CLI grouping is tested, graph resume event tracing is tested, API resume does not pass `session_id`.
- Suggested test: API `/chat` + `/approval` with mocked Langfuse keeps root trace session id consistent with the persisted session.

### P2: CLI Tests Are Mostly Headless

- Area: `cli.py`.
- Evidence: `test_cli_headless.py` covers query modes; `test_observability_cli.py` monkeypatches interactive chat.
- Missing cases: interactive permission approval, plugin install/list CLI errors, `lg-agent plugins install` offline failure, real Typer command parsing for nested commands.
- Suggested test: use Typer `CliRunner` for nested command surfaces without spawning real provider/network.

### P2: Tests Do Not Exercise Python Module Execution Without PYTHONPATH/Install

- Area: packaging usability.
- Evidence: manual audit showed `python -m langgraph_agent_blueprint` fails without editable install or `PYTHONPATH=src`.
- Suggested test/doc: either require editable install for this command or add a smoke that sets `PYTHONPATH=src` explicitly.

### P3: Some Historical Audit Docs Are Searched By Tests But Not Current Status

- Area: docs/test expectations.
- Evidence: docs contain old audit tables with `broken`, `partially_working`, and Claude Code-like source references.
- Suggested test: docs-current-status test should target README and current docs only, excluding historical audit docs.

