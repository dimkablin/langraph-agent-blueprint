# Widget Frontend Migration Plan

Date: 2026-05-08

## Recommendation

Recommended strategy: **build a TypeScript runtime frontend in `langgraph-agent-blueprint` and port selected widget presentation components behind a new runtime API/event adapter**.

This is closest to strategy D with selective extraction from strategy B:

- Do not replace the current frontend with the widget wholesale.
- Do not keep the widget's Luxms/data-analyst API client.
- Do port the chat presentation, markdown, activity rows, spinner/theme ideas, and test style.
- Do write a new API client, event reducer, runtime view models, and panels for `langgraph-agent-blueprint`.

## Why Not Drop-In Replacement

| Reason | Impact |
| --- | --- |
| Widget expects Luxms OTP auth and `/sessions/{id}/query/stream` | Current backend exposes `/chat`, `/approval`, registry routes, and batch `/chat/stream` |
| Widget event types are `token/final/tool_start/tool_end` | Runtime emits typed `RuntimeEvent` envelope with many event families |
| Widget lacks permission UI | Current runtime requires approve/reject for side-effect tools |
| Widget lacks context/attachment UI | Phase 6 runtime context providers need @mentions, trust markers, budget, errors |
| Widget settings use local mock tools/skills | Runtime registries should come from backend endpoints |
| Widget does not cover plugins/MCP/hooks/config/observability/evals | These are key runtime surfaces before frontend |

## Migration Phases

### 1. Backend API Contract Cleanup

Goal: make the backend contract frontend-stable before substantial UI work.

Backend work:

- Add live streaming endpoint using SSE or NDJSON.
- Keep batch `/chat/stream` only if documented as compatibility/debug.
- Remove or resolve duplicate `/commands`, `/skills`, `/tools` route definitions.
- Add typed frontend DTOs for sessions, events, registries, context, config, observability, and extension status.
- Add typed session detail/messages/events endpoint.
- Add context status/list/clear endpoint if the context panel is MVP.
- Add config show/explain/validate endpoints if config panel is MVP.

Widget reuse:

- SSE parsing pattern from `backend-chat-runtime.ts`.
- Contract-test style from `tests/widget-backend-connection.test.ts`.

Tests needed:

- API contract tests for chat, stream, approval, session detail, registries.
- Stream parser fixtures for each event family.
- Permission approval/rejection contract tests.

### 2. Frontend Foundation

Goal: replace the current JS shell with a typed frontend foundation.

Recommended structure:

```text
frontend/src/api/
  client.ts
  stream.ts
  schemas.ts

frontend/src/runtime/
  events.ts
  reducer.ts
  view-models.ts

frontend/src/components/chat/
frontend/src/components/events/
frontend/src/components/permissions/
frontend/src/components/sessions/
frontend/src/components/context/
frontend/src/components/extensions/
frontend/src/components/config/
```

Widget files likely reused:

- `vite.config.ts` and `tsconfig.json` patterns.
- `styles.css` theme/markdown pieces.
- `WidgetMarkdownBlock.tsx`.
- `WidgetSpinnerDisplay.tsx`.

Files rewritten:

- API client.
- Event types.
- Chat hook/reducer.
- Runtime config reader.

Tests needed:

- API client unit tests with fetch stubs.
- Stream parser tests.
- Runtime event reducer tests.
- Unknown event fallback tests.

### 3. Chat UI

Goal: implement a normal runtime chat page.

Port/adapt:

- `WidgetChatPanel`.
- `WidgetComposer`.
- `WidgetMessageList`.
- `WidgetMessageBubble`.
- `WidgetActivityFeed`.

Required changes:

- Replace `WidgetStreamEvent` with runtime `RuntimeEvent`.
- Build assistant message state from `model_token`, `final_response`, and `error`.
- Render tool events from `tool_call_started/finished/error`.
- Render skill/subagent/MCP/hook/context events as timeline rows or grouped badges.
- Keep unknown event rendering, collapsed by default.
- Replace data analyst quick suggestions with runtime-relevant examples or remove.

Backend gaps:

- Live stream endpoint for smooth draft UX.
- Stable event payload fields for frontend rendering.

Tests needed:

- Chat sends message and renders final response.
- Runtime event timeline groups tools/skills/subagents.
- Unknown events render safely.
- Error events render predictably.

### 4. Permission UI

Goal: support side-effect tool approval without frontend owning policy.

Build:

- Permission modal or anchored approval bar.
- Approve/reject API client.
- View model for `tool_call_id`, `tool_name`, `action`, `risk`, `args_summary`, `reason`, `session_id`, `thread_id`.

Widget reuse:

- General modal/card style from settings overlay.
- Button/icon style.

Backend gaps:

- Ensure `permission_required` payload is stable and redacted.
- Ensure approval responses preserve `session_id` and `thread_id`.

Tests needed:

- Permission modal renders risk/action/args summary.
- Approve sends correct payload.
- Reject sends correct payload.
- Rejection result appears in event timeline.

### 5. Sessions And Context Panels

Goal: make persistence and context visible.

Sessions:

- List sessions.
- Open session detail.
- Resume session.
- Export transcript.
- Show child run count and link when API exists.

Context:

- Show parsed refs.
- Show fragments, trust markers, budget, errors.
- Add composer support for @mention syntax.
- Add attachment metadata list.

Widget reuse:

- Sidebar/card visual language from settings overlay.
- Composer base.

Backend gaps:

- Typed session detail endpoint.
- Context list/detail endpoint or sufficiently complete stream/session metadata.
- Export/download endpoint if UI export is MVP.

Tests needed:

- Session list and resume.
- @file prompt preserves text and shows context event.
- Context budget/trust markers render.

### 6. Extension Panels

Goal: expose runtime surfaces without duplicating runtime logic.

Panels:

- Tools/skills/commands from registry endpoints.
- MCP server/tool/resource/prompt status from `/mcp`.
- Plugins from future plugin status endpoint.
- Hooks from future hooks status endpoint.
- Config/observability from future status endpoints.

Widget reuse:

- Settings overlay tabs/cards as a visual reference only.

Backend gaps:

- Plugin status endpoint.
- Hook status endpoint.
- Config and observability endpoints.
- More typed registry DTOs.

Tests needed:

- Registry panels render backend snapshots.
- Diagnostics/warnings render.
- Disabled/unavailable entries render without crashing.

### 7. Later UI

Post-MVP:

- Eval dashboard.
- Plugin install/update/remove UI.
- MCP resource browser.
- Hook editor.
- Subagent transcript viewer.
- Artifact workbench.
- Marketplace.
- Visual graph/execution viewer.

## Frontend MVP Scope

Recommended MVP after backend contract cleanup:

1. Chat page with live event timeline.
2. Permission modal/bar.
3. Runtime side panel for tools, skills, commands, and status.
4. Sessions panel with list/resume/export.
5. Context panel with refs/fragments/budget/errors.
6. MCP/plugins/config/observability panels as read-only status where endpoints exist.

Not MVP:

- Full plugin install UI.
- Eval dashboard.
- MCP resource browser/editor.
- Hook editor.
- Subagent transcript viewer.
- Marketplace.

## Test Strategy

Frontend tests:

- API client request/response tests.
- Stream parser tests.
- Runtime event reducer tests.
- Chat send/stream/final response tests.
- Permission modal approve/reject tests.
- Context composer and context panel tests.
- Session panel tests.
- Unknown event fallback tests.
- Extension panel snapshot/diagnostic tests.

Backend/frontend contract tests:

- OpenAPI or DTO snapshot for chat, approval, sessions, registries.
- Stream event fixture tests for core/tool/permission/skill/context/subagent/MCP/hook events.
- Approval flow contract tests.
- Context attachment contract tests.

E2E later:

- Playwright with fake provider.
- Send chat message.
- Approve/reject permission.
- Attach `@README.md`.
- Resume session.
- Show plugin/MCP status.

## Implementation Notes

- Keep frontend thin: no direct tool execution, no permission policy decisions, no graph orchestration.
- Treat backend events as source of truth.
- Maintain a typed view-model layer between runtime events and visual components.
- Keep old widget mock runtime only as local demo/test fixture if it is rewritten to emit runtime events.
- Do not carry Luxms auth into the main runtime frontend unless a future auth phase defines it.
- Verify source text encoding before copying Russian labels from `WidgetAccountSettings.tsx`.

