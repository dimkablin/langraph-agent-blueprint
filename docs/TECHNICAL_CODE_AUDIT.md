# Technical Code Audit

Date: 2026-05-07

Scope: audit-only review of the Python/LangGraph runtime, CLI/API adapters, tools, skills, plugins, hooks, MCP, Langfuse observability, storage, tests, docs, packaging, and frontend static contract. Production code and tests were not changed.

## Baseline

- `git status --short`: no tracked changes; Git printed warnings about `C:\Users\dimka/.config/git/ignore` permission.
- First combined baseline command timed out at 120s while pytest was still running.
- `python -m pytest -q`: passed, 100%.
- `npm.cmd --prefix frontend run test:static`: passed.
- `python -m langgraph_agent_blueprint ...` fails without editable install or `PYTHONPATH=src`.
- With `PYTHONPATH=src` and `LLM_PROVIDER=fake`, `--help`, `doctor`, `query "hello"`, and `query "/status"` run.

## Post-Audit Fix Status

Batch 1 and Batch 2 fixes on 2026-05-07 closed the P0 storage/API identifier risk and the P1 findings for mutable tool state, ambiguous file edits, web fetch guardrails, hardwired Superpowers policy, `remember` side effects in `skill_router`, MCP discovery during dependency construction, invalid MCP config diagnostics, plugin git timeout, API approval trace session id, and hook applier nested-list mutation. Remaining P1/P2 items are primarily architecture/maintainability cleanup such as service splitting and MCP cwd policy.

## Overall Status

The project is in a solid reference-runtime state: the graph is the central workflow owner, tests cover many historical runtime bugs, permissions are mostly metadata-driven, Langfuse trace scoping has strong fake-client regression coverage, MCP uses an offline fake stdio server in tests, and docs now describe most implemented limitations.

The remaining risks are not "everything is broken" risks. They are mostly hardening and maintainability issues expected after several large phases: storage identifier validation, overly broad services, generic extension point cleanup, and some stale/historical documentation still presented near current README material.

## Issue Counts

- P0: 1
- P1: 11
- P2: 15
- P3: 7

P0 is reserved for concrete correctness/security risk. Most findings are P1/P2 because the runtime works but needs hardening before more phases.

## Top 10 Risks

| Priority | Area | Finding | Evidence |
| --- | --- | --- | --- |
| P0 | Storage/API | User-supplied `session_id` is used as a filesystem path segment without validation. | `src/langgraph_agent_blueprint/storage/session_storage.py:29`, `src/langgraph_agent_blueprint/api/schemas.py:13` |
| P1 | Tools/state | `ToolExecutionContext` exposes whole graph state to tools, so tools can inspect or mutate arbitrary state outside typed effects. | `src/langgraph_agent_blueprint/tools/base.py:40`, `src/langgraph_agent_blueprint/services/tool_execution_service.py:34` |
| P1 | Plugins/policy | Superpowers activation is wired through direct imports in the graph policy node instead of a generic plugin policy contribution. | `src/langgraph_agent_blueprint/graph/nodes/plugin_policy.py:7`, `src/langgraph_agent_blueprint/plugins/superpowers.py:66` |
| P1 | Skills | `remember` has name-specific durable side effects inside `skill_router_node`, bypassing the normal tool/effect architecture. | `src/langgraph_agent_blueprint/graph/nodes/skill_router.py:60` |
| P1 | File edits | `edit_text` replaces the first match but its error text says "exactly once"; ambiguous edits are not rejected. | `src/langgraph_agent_blueprint/services/file_service.py:52` |
| P1 | MCP lifecycle | `build_dependencies` calls `mcp_service.discover()`, which can start configured stdio servers during dependency construction. | `src/langgraph_agent_blueprint/dependencies.py:87` |
| P1 | MCP config diagnostics | Invalid MCP server configs are silently skipped, so users may see no server instead of a structured config error. | `src/langgraph_agent_blueprint/services/mcp_service.py:357` |
| P1 | Network safety | `web_fetch` has no scheme/host policy or body-size cap before `response.text` is materialized. | `src/langgraph_agent_blueprint/services/web_service.py:20` |
| P1 | Observability/API resume | API approval/resume does not pass a session id to `runtime.resume`, so the Langfuse root trace can use `thread_id` as session id before result hydration. | `src/langgraph_agent_blueprint/api/server.py:56`, `src/langgraph_agent_blueprint/graph/builder.py:176` |
| P2 | Maintainability | `observability_service.py`, `mcp_service.py`, `plugin_service.py`, and `builder.py` are the largest modules and carry multiple responsibilities. | line-count audit |

## What Is Good

- Graph edges express the main workflow and tool loop.
- Tool routing is metadata-driven through `ToolRuntimeMetadata.route`.
- Permission decisions are metadata-driven through `ToolPermissionMetadata`.
- Runtime boundary models exist for tools, events, commands, permissions, skills, plugins, hooks, MCP, sessions, and observability.
- Plugin hooks are declarative/data-only and use controlled `HookResult` application.
- MCP tools are registered into the normal `ToolRegistry` and are conservative by default.
- Langfuse is optional, no-op when disabled, and runtime event export is trace-scoped.
- Tests cover many e2e paths, including interrupt/resume, MCP permissions, hooks, Superpowers, and Langfuse trace scoping.

## What Needs Cleanup

- Validate external identifiers (`session_id`, `thread_id`, export names where applicable) before using them in filesystem or checkpoint paths.
- Split large services into protocol/client/mapper/status pieces.
- Move plugin policy into declarative or registered plugin policy contributions.
- Remove skill-name-specific side effects from `skill_router_node`.
- Make MCP discovery lazy or explicit per command path.
- Add stronger config diagnostics for invalid MCP and plugin records.
- Tighten network fetch security and output bounding.
- Remove stale current-sounding README references to old audited Claude Code-like source context or clearly mark them historical.

## Recommended Next Fixes

1. Fix storage/API identifier validation first.
2. Make tool execution context read-only and remove direct graph state exposure from tools.
3. Refactor Superpowers policy into a generic plugin policy contribution.
4. Split MCP lifecycle/discovery/invocation and make server startup lazy/explicit.
5. Add exact-once edit validation and regression tests.
6. Add SSRF/body-size guardrails to web fetch.
7. Refresh README and `.env.example` to match current runtime.
