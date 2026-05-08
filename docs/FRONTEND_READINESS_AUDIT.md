# Frontend Readiness Audit

Audit date: 2026-05-08

Scope: audit-only review of backend/runtime/API/frontend readiness for a normal React frontend. Production code, frontend code, and tests were not changed during this audit.

## Baseline

| Check | Result | Notes |
| --- | --- | --- |
| `git status --short` | clean | Git prints `unable to access C:\Users\dimka/.config/git/ignore: Permission denied`; no repo changes were listed. |
| `python -m pytest -q` | passed | Full backend test suite passed. |
| `npm.cmd --prefix frontend run test:static` | passed | 3 static frontend checks passed. |
| `$env:PYTHONPATH="src"; python -m langgraph_agent_blueprint eval run --all` | passed | 18 scenarios passed. `.eval_runs` artifact was removed after the run. |
| `npm.cmd --prefix frontend run build` | passed after escalation | First sandbox run failed with Vite `spawn EPERM`; rerun with approved escalation built successfully. |
| `lg-agent doctor` | not run | `lg-agent` executable is not installed on PATH. |
| `$env:PYTHONPATH="src"; python -m langgraph_agent_blueprint doctor` | passed | Reports runtime status ok; local Langfuse config is enabled but SDK is missing, so observability status is `missing_dependency`. |
| `$env:PYTHONPATH="src"; python -m langgraph_agent_blueprint config validate` | passed | `Config loaded successfully`. |

Baseline status: green for backend tests, frontend static tests, eval replay, and Vite build after sandbox escalation.

## Current Frontend State

Frontend stack:

- React 19
- Vite 7
- JavaScript/JSX, not TypeScript
- `lucide-react`
- No router, state library, schema generator, or OpenAPI client

Package scripts:

- `dev`: Vite dev server on `127.0.0.1:5173`
- `build`: Vite production build
- `preview`: Vite preview on `127.0.0.1:4173`
- `test:static`: static contract smoke over source files

Files:

- `frontend/src/api.js`: thin fetch wrapper for `/chat`, `/approval`, `/commands`, `/skills`, `/tools`.
- `frontend/src/App.jsx`: single-page CLI-like shell, local transcript state, permission prompt wiring.
- `frontend/src/components.jsx`: presentational shell, status bar, hint panel, permission prompt.
- `frontend/src/commandHints.js`: fallback static command/tool/skill hints.
- `frontend/src/styles.css`: dense terminal-style UI.
- `frontend/tests/frontend-static.test.mjs`: static checks that the frontend shell uses graph-facing endpoints and does not call tool execution endpoints.

What is connected to backend:

- Chat turn through `POST /chat`.
- Approval resume through `POST /approval`.
- Registry snapshots through `GET /commands`, `GET /skills`, `GET /tools`.
- CORS is tested for Vite origin.

What is still mock/static shell:

- Fallback slash/tool/skill hints are hardcoded in `commandHints.js`.
- Event rendering is a local filter in `App.jsx` with a hardcoded event allowlist.
- There is no real stream client. The page waits for `POST /chat` to return one `ChatResponse`.
- No frontend schema/type layer exists.
- No UI exists for sessions, context, plugins, MCP, hooks, config, observability, evals, or child runs.

Existing UI surfaces:

- Terminal transcript.
- Message input.
- Runtime status bar with session/thread ids.
- Hint side panel for commands/tools/skills.
- Permission bar for approve/reject.
- Event lines for selected runtime events.

Missing UI surfaces:

- Real streaming event timeline.
- Session list/detail/resume/export.
- Context refs/fragments/budget/errors.
- Plugin, MCP, hook, config, observability panels.
- Subagent child-run list/detail.
- Memory/todo panels.
- Eval/replay panel.
- Export download/result UX.

Business logic assessment:

- The frontend does not execute tools, resolve permissions, call LangGraph services, or route workflow locally.
- It does contain a small hardcoded event classifier and fallback hints. That is acceptable for the current shell, but a production frontend should move event normalization into typed `runtime/events` modules and prefer backend registry data over static hints.

## Readiness Scores

| Area | Status | Score | Reason |
| --- | --- | --- | --- |
| Runtime MVP | ready | 8/10 | Graph, tools, skills, permissions, sessions, context, subagents, evals, config, plugins are implemented and tested. |
| API contract | partial | 5/10 | Core chat and registry endpoints exist, but many runtime surfaces are CLI-only or command-only. |
| Streaming contract | partial | 4/10 | `AssistantGraphRuntime.stream` exists and CLI stream-json works; FastAPI `/chat/stream` returns a list, not SSE/WebSocket/chunked JSON. |
| Approval UX backend | ready with caveats | 7/10 | Permission payload has required modal fields and approval endpoint works; nested subagent approval remains limited. |
| Current frontend | shell only | 3/10 | Useful proof shell, not a full runtime UI. |
| Frontend build/test baseline | ready | 8/10 | Static tests and build pass in local environment; build needs sandbox escalation due Vite subprocess spawn. |

## Highest-Risk Findings

1. **No real HTTP streaming transport.**
   `POST /chat/stream` returns `list(runtime.stream(...))`. This gives frontend a batch of events after completion, not live event delivery.

2. **Many frontend-relevant runtime surfaces are only available as slash commands or CLI commands.**
   Config explain/validate, plugins install/update/remove, hooks, context, observability, memory/todo, evals, export, and child runs need first-class HTTP endpoints or a documented command-through-chat fallback.

3. **API routes are duplicated for `/commands`, `/skills`, and `/tools`.**
   `server.py` defines inline endpoints and also includes routers with the same paths. FastAPI currently accepts this, but it makes OpenAPI/client generation ambiguous and should be cleaned before building a typed frontend client.

4. **Frontend has no typed contract layer.**
   `api.js` returns raw JSON and components inspect ad hoc fields. A normal frontend should introduce typed API modules and runtime event reducers before UI growth.

5. **Session detail endpoint returns raw storage shape.**
   `GET /sessions/{session_id}` exposes storage records directly. A frontend-facing DTO should normalize messages, events, tool calls, child runs, and export refs.

## What Is Good

- The existing frontend uses graph-facing endpoints only.
- Permission approval is already modeled end-to-end with API tests.
- CORS for local Vite origin is tested.
- Runtime events are typed in Python through `RuntimeEvent` and `EventType`.
- Context, plugin, MCP, subagent, and eval features have deterministic eval scenarios.
- Backend validation rejects unsafe runtime ids at API boundaries.

## Readiness Conclusion

The backend/runtime is ready enough to begin frontend implementation if the frontend starts with a thin chat/session shell and treats missing panels as read-only placeholders. For a production-grade frontend, the first backend/frontend integration cleanup should be:

1. Introduce a real streaming endpoint contract.
2. Remove duplicate route definitions and stabilize OpenAPI.
3. Add missing frontend-facing status/list/detail endpoints for runtime panels.
4. Add generated or manually maintained TypeScript schemas for API responses and runtime events.

