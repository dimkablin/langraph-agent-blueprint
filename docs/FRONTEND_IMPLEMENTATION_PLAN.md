# Frontend Implementation Plan

Audit date: 2026-05-08

Goal: build a thin frontend over the existing FastAPI/LangGraph runtime. The frontend must display runtime state and send user/API actions; it must not execute tools, own workflow routing, duplicate permission policy, or bypass the graph.

## Recommended MVP Scope

### 1. Chat Page

Features:

- Message input.
- Runtime event timeline.
- Final assistant response.
- Error display.
- Busy/idle/run status.
- Session/thread id display.

Backend dependency:

- `POST /chat`.
- Real streaming endpoint once added.

Initial fallback:

- Use current `POST /chat` response for non-live MVP.
- Treat `/chat/stream` as batch events until SSE/NDJSON/WebSocket is implemented.

### 2. Permission Modal

Features:

- Modal/bar for `permission_required`.
- Show tool name, action, risk, args summary, reason.
- Approve/reject with reason.
- Show resolved approval/rejection result.

Backend dependency:

- `POST /approval`.

Implementation note:

- Store `session_id`, `thread_id`, and `tool_call_id` with modal state.
- Prefer sending typed `PermissionDecision` once API schema is tightened.

### 3. Runtime Side Panel

Features:

- Commands.
- Tools.
- Skills.
- Basic status.

Backend dependency:

- `GET /commands`.
- `GET /tools`.
- `GET /skills`.
- Optional `GET /status` or diagnostics endpoint later.

### 4. Sessions Panel

Features:

- List sessions.
- Open session detail.
- Resume by selecting session.
- Show events/messages/tool calls.
- Export transcript trigger once endpoint exists.

Backend dependency:

- `GET /sessions`.
- `GET /sessions/{session_id}`.
- Future export endpoint.

### 5. Context Panel

Features:

- Current context refs/fragments.
- Budget meter.
- Trust markers.
- Context errors.
- `@mention` help.

Backend dependency:

- Context events in chat responses.
- Future `GET /sessions/{session_id}/context`.

### 6. Plugins/MCP Panel

MVP:

- Read-only plugin status once endpoint exists.
- MCP server/tool/resource/prompt status through `GET /mcp`.

Defer:

- Plugin install/update/remove UI.
- MCP resource browser/editor.
- Hook editor.

### 7. Observability/Config Panel

MVP:

- Read-only config show/explain/validate once endpoints exist.
- Observability status once endpoint exists.

Defer:

- Editing config in UI.
- Langfuse live smoke or key entry.

## Non-MVP Frontend

- Plugin install/update/remove management UI.
- Eval dashboard.
- MCP resource browser with prompt insertion.
- Hook editor.
- Subagent transcript viewer beyond simple child-run cards.
- Marketplace.
- Visual LangGraph editor.
- IDE/LSP integrations.
- Background task/team management.

## Proposed Frontend Architecture

Current frontend is JavaScript. For a normal maintainable frontend, migrate the app code to TypeScript before the UI grows.

Suggested structure:

```text
frontend/src/api/
  client.ts
  chat.ts
  sessions.ts
  registries.ts
  mcp.ts
  config.ts
  plugins.ts
  schemas.ts

frontend/src/runtime/
  types.ts
  events.ts
  reducer.ts
  selectors.ts

frontend/src/components/chat/
frontend/src/components/events/
frontend/src/components/permissions/
frontend/src/components/sessions/
frontend/src/components/context/
frontend/src/components/plugins/
frontend/src/components/mcp/
frontend/src/components/config/
frontend/src/components/observability/
frontend/src/components/layout/
```

State model:

- API client owns HTTP and stream parsing.
- Runtime reducer owns event-derived UI state.
- Components render typed props.
- Unknown event fallback keeps the UI forward-compatible.
- Backend registry snapshots drive tools/skills/commands lists.

Rules:

- No direct tool execution in frontend.
- No local permission policy.
- No graph routing in frontend.
- No hardcoded backend enum values inside presentation components.
- No raw `dict` assumptions in UI components after TypeScript schema layer exists.

## Backend Work Before Full Frontend

| Work item | Why it matters | Priority |
| --- | --- | --- |
| Implement live stream endpoint | Required for token/event timeline UX. | P1 |
| Remove duplicate registry routes | Required for clean OpenAPI and typed client generation. | P1 |
| Add typed frontend DTOs | Prevents UI from depending on raw storage/runtime dicts. | P1 |
| Add session context/child-run endpoints | Needed for context and subagent panels. | P1 |
| Add config/observability read-only endpoints | Needed for status/config panel. | P2 |
| Add plugin/hook read-only endpoints | Needed for extension panels. | P2 |
| Add export trigger/download endpoint | Needed for sessions panel export UX. | P2 |
| Add upload endpoint | Needed for file drag/drop beyond `@mention` refs. | P2 |
| Keep plugin install UI deferred | Trust UX and path/git policy need deliberate design. | P3 |

## Test Strategy

Frontend unit/static tests:

- API client request/response mapping.
- Stream parser framing.
- Runtime event reducer.
- Unknown event fallback.
- Permission modal approve/reject payloads.
- Context budget/trust rendering.
- Session list/detail rendering.

Backend/frontend contract tests:

- OpenAPI route snapshot after duplicate routes are removed.
- `ChatRequest`/`ChatResponse` schema contract.
- `ApprovalRequest`/approval response contract.
- Runtime event fixture contract.
- Context attachment contract.
- Registry snapshot contract.

E2E tests later:

- Start FastAPI with fake provider.
- Send chat message.
- See final response.
- Trigger permission and approve/reject.
- Use `@README.md` context.
- Resume a session.
- Show MCP/plugin/config panels.

Recommended runner:

- Keep `frontend/tests/frontend-static.test.mjs` for cheap guardrails.
- Add component/reducer tests once TypeScript modules exist.
- Add Playwright only when the first real interactive frontend is present.

## Implementation Order

1. Backend contract cleanup: live stream, duplicate routes, DTOs.
2. TypeScript frontend API/runtime layers.
3. Chat/timeline UI backed by real responses.
4. Permission modal.
5. Session panel.
6. Context panel.
7. Read-only MCP/plugin/config/observability panels.
8. Optional export/download.
9. Later: eval dashboard and plugin management.

