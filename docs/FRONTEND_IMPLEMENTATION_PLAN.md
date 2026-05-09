# Frontend Implementation Plan

Audit date: 2026-05-08

Goal: build a thin frontend over the existing FastAPI/LangGraph runtime. The frontend must display runtime state and send user/API actions; it must not execute tools, own workflow routing, duplicate permission policy, or bypass the graph.

## Implemented MVP Scope

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
- `POST /chat/stream` SSE.

Initial fallback:

- Use `POST /chat` response for non-streaming fallback.
- Use `/chat/stream` SSE `StreamFrame` objects for the live event timeline.

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
- Send typed `PermissionDecisionDTO(tool_call_id, decision, reason?)`; legacy `{approved}` support exists only for the current shell.

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
- Read-only status endpoints: `GET /plugins`, `/hooks`, `/config`, `/config/explain`, `/config/validate`, `/observability`, `/mcp/snapshot`.

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
- `GET /sessions/{session_id}/events`.
- `GET /sessions/{session_id}/messages`.
- `GET /sessions/{session_id}/child-runs`.
- `POST /sessions/{session_id}/export`.

### 5. Context Panel

Features:

- Current context refs/fragments.
- Budget meter.
- Trust markers.
- Context errors.
- `@mention` help.

Backend dependency:

- Context events in chat responses.
- `GET /sessions/{session_id}/context`.

### 6. Plugins/MCP Panel

MVP:

- Read-only plugin status once endpoint exists.
- MCP server/tool/resource/prompt status through passive `GET /mcp/snapshot`; explicit discovery remains on `GET /mcp`.

Defer:

- Plugin install/update/remove UI.
- MCP resource browser/editor.
- Hook editor.

### 7. Observability/Config Panel

MVP:

- Completed: Settings opens as a separate tabbed app view rather than a small drawer.
- Completed: Settings renders read-only config show/explain/validate, runtime status, extension status, MCP snapshot, plugin status, and skill registry data.
- Completed: UI-only preferences persist locally and do not write backend config.

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

Current frontend is TypeScript React. The old JavaScript CLI-like shell was replaced by typed API/runtime layers and component panels.

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
frontend/src/components/settings/
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

## Remaining Frontend/Backend Work

| Work item | Why it matters | Priority |
| --- | --- | --- |
| Improve subagent transcript UI | Current timeline shows subagent events; a dedicated transcript viewer is still deferred. | P2 |
| Add export download endpoint | Export trigger exists; direct download/read is still missing. | P2 |
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

- OpenAPI route snapshot guarding one canonical operation per path/method.
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

1. Completed: TypeScript frontend API/runtime layers on top of the stabilized backend contract.
2. Completed: Chat + SSE event timeline.
3. Completed: Chat/timeline UI backed by real responses.
4. Completed: Permission approval bar.
5. Completed: Session panel.
6. Completed: Context panel.
7. Completed: Basic read-only MCP/plugin/config/observability status summary.
8. Completed: Read-only tabbed Settings page with local-only UI preferences.
9. Next: richer panels, upload/download, subagent detail, eval dashboard, settings schema/patch API, and plugin management.
