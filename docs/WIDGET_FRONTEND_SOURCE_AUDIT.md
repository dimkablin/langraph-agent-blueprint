# Widget Frontend Source Audit

Date: 2026-05-08

This audit checks whether the external widget project can be used as the frontend base for `langgraph-agent-blueprint`. It is audit-only: no backend, frontend, test, or widget source files were changed.

## Paths Checked

| Area | Path | Result |
| --- | --- | --- |
| Current runtime project | `C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint` | Present |
| External widget source | `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\llm-data-analyst-dev\widget` | Present |

## Baseline

Current runtime project:

| Check | Result | Notes |
| --- | --- | --- |
| `git status --short` | Clean production code; existing untracked frontend-readiness docs | Git emitted global ignore permission warning |
| `python -m pytest -q` | Passed | Full backend/runtime suite |
| `npm.cmd --prefix frontend run test:static` | Passed | Current React CLI shell static contract tests |
| `$env:PYTHONPATH="src"; python -m langgraph_agent_blueprint eval run --all` | Passed | 18 eval scenarios passed |

Widget project:

| Check | Result | Notes |
| --- | --- | --- |
| `Test-Path ...\widget` | `True` | Widget exists |
| `git status --short` | No tracked changes reported | Git emitted global ignore permission warning and one `tmp_workspace_temp` permission warning |
| `dir` | Present | `.npm-cache`, `dist`, `node_modules`, `src`, `tests`, `package.json`, `package-lock.json`, `README.md`, `tsconfig.json`, `vite.config.ts` |
| `npm run test` | Blocked by PowerShell `npm.ps1` policy | Re-run with `npm.cmd` |
| `npm.cmd run test` | Passed after allowing Vite/Vitest worker execution | 3 files, 27 tests passed |
| `npm.cmd run build` | Passed | Vite warned that one JS chunk is over 500 kB |

## Stack

| Category | Widget |
| --- | --- |
| Package manager | npm, `package-lock.json` |
| Framework | React 18.3.1 |
| Language | TypeScript, strict mode |
| Build tool | Vite 6.3.5 |
| Styling | Tailwind CSS 4 via `@tailwindcss/vite`, global CSS tokens |
| Icons | `lucide-react` |
| Animation | `motion` |
| Markdown | `react-markdown` + `remark-gfm` |
| Tests | Vitest + Testing Library + jsdom |
| Routing | None |
| State management | Local React state and custom hooks |

## Source Structure

| Path | Purpose |
| --- | --- |
| `src/chat/backend-chat-runtime.ts` | Luxms/backend adapter, auth, session creation, SSE parsing |
| `src/chat/mock-chat-runtime.ts` | Deterministic mock stream with tokens, reasoning, tool rows, artifacts |
| `src/chat/widget-chat-runtime.ts` | Runtime selector between backend and mock |
| `src/chat/useWidgetChatAgent.ts` | Main chat state hook and stream event reducer |
| `src/types/backend-types.ts` | Widget-specific request, response, event, artifact, message types |
| `src/components/chat/` | Chat panel, composer, message list, bubbles, tool activity feed |
| `src/components/artifacts/` | Table/json/value/plot artifact renderers |
| `src/components/settings/` | Account/settings overlay with local mock tools/skills/config controls |
| `src/config/widget-config.ts` | Browser-global widget config reader |
| `src/settings/widget-chat-settings.ts` | Widget-local display/runtime settings |
| `src/styles.css` | Tailwind import, theme tokens, markdown styles, custom animations |
| `tests/` | Backend adapter, artifact contract, mock runtime, UI behavior tests |

## API Client Behavior

The widget has a real backend client, but it is not compatible with the current `langgraph-agent-blueprint` API.

Current widget backend flow:

1. Read `window.__LLM_ANALYST_WIDGET_DEV__`.
2. If `mode === "backend"`, require `luxmsIdentity.login_as`.
3. POST `/auth/luxms/otp-login`.
4. Cache bearer token and backend session id in module-level memory.
5. POST `/sessions` once to create a session.
6. POST `/sessions/{session_id}/query/stream`.
7. Parse `text/event-stream` blocks into widget events.

Widget query request:

```json
{
  "query": "user prompt",
  "use_history": true,
  "include_reasoning": true,
  "analysis_depth": "medium"
}
```

Current runtime chat request:

```json
{
  "message": "user prompt",
  "session_id": null,
  "thread_id": null,
  "attachments": []
}
```

The widget already avoids localStorage/sessionStorage in backend mode and keeps backend token in memory only. That is a good security posture, but the auth model is specific to the old data analyst backend and should not be carried over as-is.

## Event Model

Widget event types:

| Widget event | Current widget use |
| --- | --- |
| `token` | Appends assistant draft text |
| `final` | Commits final assistant message |
| `reasoning`, `reasoning_token` | Shows thinking trace |
| `thinking_start`, `thinking_end` | Creates thinking blocks |
| `tool_start`, `tool_end` | Creates tool use/result blocks |
| `phase` | Currently ignored in hook |
| `execution_graph` | Stores visual execution graph payload |
| `error` | Shows error text |

Runtime event types are broader and wrapped as:

```json
{
  "id": "...",
  "type": "tool_call_started",
  "timestamp": "...",
  "session_id": "...",
  "node": null,
  "severity": "info",
  "data": {}
}
```

Compatibility status: partial. The widget has useful rendering concepts, but needs a new event adapter/reducer for `RuntimeEvent` payloads, ids, session/thread metadata, permission events, context events, MCP, hooks, subagents, config, observability, and eval events.

## Current Frontend Reality

The widget is a standalone Vite app. It is not embedded in `langgraph-agent-blueprint`, and it does not know about LangGraph runtime concepts directly.

Real parts:

- React/TypeScript shell.
- Mock stream runtime with deterministic events.
- Backend-mode fetch/SSE client.
- Chat UI with streaming draft.
- Tool activity rows.
- Artifact chips/renderers.
- Markdown rendering.
- Settings overlay.
- Vitest/Testing Library coverage.

Mock or old-backend-specific parts:

- Luxms auth.
- `/sessions/{id}/query/stream` API.
- Data analyst query settings such as `analysisDepth`.
- Mock tool names `planner_tool`, `sql_tool`, `plotly_tool`.
- Data analyst artifacts and metrics.
- Settings panel tools/skills are local constants, not backend registry data.
- Export button is disabled.
- Session memory panel is placeholder.

## Reusable Assets

| Area | Reuse Level | Notes |
| --- | --- | --- |
| React/TypeScript/Vite/Tailwind test setup | Reuse with adapter | Stronger than current JS shell; package versions differ from current frontend |
| Chat panel layout | Reuse with adapter | Good first screen for runtime frontend |
| Composer | Reuse with adapter | Needs @mention, attachments, disabled states, slash command hints |
| Message bubbles | Reuse with adapter | Good markdown/message styling |
| Tool activity feed | Reuse with adapter | Map runtime tool/skill/subagent/MCP/context events into generic timeline items |
| Markdown block | Reuse as-is or lightly adapted | Needs URL safety review for external links |
| Spinner variants | Reuse with adapter | Visual polish is useful |
| Artifact surface | Partial reuse | Data analyst artifact schema does not match current runtime artifact model yet |
| Settings overlay | Reuse as visual reference | Current data is local/mock and text encoding appears broken in source output |
| Tests | Reuse patterns | Existing tests validate contracts and UI behavior; assertions should be rewritten for runtime events |

## Must Be Rewritten

- API client and DTO layer.
- Runtime event types and reducer.
- Approval/resume client and UI.
- Session list/detail/export client.
- Context/attachments UI and state model.
- Plugins/MCP/hooks/config/observability/eval panels.
- Old Luxms auth/session assumptions.
- Data analyst-specific artifacts unless runtime adds compatible artifacts.
- Local mock tools/skills/settings data.

## Main Risks

| Risk | Why It Matters | Recommendation |
| --- | --- | --- |
| API mismatch | Widget cannot talk to current backend without an adapter | Build a new typed API client for `langgraph-agent-blueprint` |
| Event taxonomy mismatch | Widget stream reducer ignores most runtime event types | Introduce `RuntimeEvent` types and a tolerant reducer |
| Missing permission UX | Runtime requires approval/rejection UI | Add dedicated permission modal/bar from runtime payload |
| Missing context UX | Runtime supports context refs/attachments/trust/budget | Extend composer and side panel before using context-heavy workflows |
| Mock registry data | Settings panel presents fake tools/skills | Drive panels from backend endpoints |
| Old auth model | Luxms OTP does not apply to current runtime | Remove or isolate behind a future auth adapter |
| Global mutable widget auth cache | Module-level cache is acceptable for small widget but not ideal app state | Move session/token state into typed API/runtime client if auth is added |
| Large bundle warning | Build emits a >500 kB chunk | Consider code splitting after migration |
| Encoding artifacts | Several Russian labels appear mojibake in shell output | Verify source encoding before reuse or rewrite labels |

## Recommendation

Do not replace the current frontend with the widget as-is. Use the widget as a high-quality visual/component donor and rebuild the runtime integration layer around `langgraph-agent-blueprint` API contracts.

Recommended strategy: create a TypeScript runtime frontend in the main project, port the widget's chat presentation components selectively, and replace the API client, event reducer, settings panels, and old data analyst assumptions with runtime-specific contracts.

