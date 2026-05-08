# Widget Component Inventory

Date: 2026-05-08

Status values:

- `reuse_as_is`: can likely move with minimal changes.
- `reuse_with_adapter`: useful component, but data/API/event contract must change.
- `rewrite`: concept is needed, implementation is too coupled.
- `discard`: not useful for `langgraph-agent-blueprint`.
- `needs_review`: useful but requires deeper visual/UX review during implementation.

| Component/File | Purpose | Dependencies | API Assumptions | Reusable? | Migration Notes |
| --- | --- | --- | --- | --- | --- |
| `src/WidgetApp.tsx` | Root renders `WidgetChatPanel` | React | None | `reuse_with_adapter` | Current root is too small to matter; main project will need app routing/layout. |
| `src/components/chat/WidgetChatPanel.tsx` | Full-page chat shell, header, settings overlay, message list, composer | React, lucide, widget config, backend model label, chat hook | Calls `/runtime/model` in backend mode through Luxms auth helper | `reuse_with_adapter` | Good visual shell. Replace config/model/status wiring with runtime API/status endpoints. |
| `src/components/chat/WidgetComposer.tsx` | Textarea, send/stop buttons, quick suggestions | React, lucide | Sends raw prompt only | `reuse_with_adapter` | Needs @mention parsing hints, attachments button/drop zone, slash command hints, permission-disabled state. Quick suggestions are data-analyst-specific. |
| `src/components/chat/WidgetMessageList.tsx` | Empty state, message rendering, streaming draft block | motion, markdown, activity feed, spinner | Expects widget `ChatMessage`, stream draft, blocks, tools | `reuse_with_adapter` | Good structure. Replace message/event types with runtime view model derived from `RuntimeEvent`. |
| `src/components/chat/WidgetMessageBubble.tsx` | User/assistant bubble, markdown, metrics, artifact chips, retry/copy | motion, lucide, artifacts | Expects `metrics`, `artifacts`, data analyst message model | `reuse_with_adapter` | Keep bubble and action pattern. Replace metrics/artifacts with runtime metadata/artifact refs. |
| `src/components/chat/WidgetActivityFeed.tsx` | Thinking blocks and tool rows | React, lucide, spinner, markdown | Expects `AssistantBlock` and `StreamToolCall` from widget events | `reuse_with_adapter` | Most valuable piece for event timeline. Needs generic runtime event grouping and unknown-event fallback. |
| `src/components/markdown/WidgetMarkdownBlock.tsx` | Markdown renderer with GFM and custom wrappers | react-markdown, remark-gfm | None | `reuse_as_is` | Keep with URL/link safety review and styling namespace adjustments. |
| `src/components/WidgetSpinnerDisplay.tsx` | Spinner variants | Tailwind classes | None | `reuse_as_is` | Good polished loading indicators. |
| `src/components/artifacts/WidgetArtifactSurface.tsx` | Renders table/json/value/plot payloads | Widget artifact schema | Expects `ArtifactPayload` with `data.format` | `reuse_with_adapter` | Useful if runtime standardizes artifacts. Otherwise keep as optional renderer for compatible artifact refs. |
| `src/components/artifacts/artifact-contract.ts` | Type guard for supported artifact formats | Widget artifact schema | `table/split`, `json/json`, `value/value`, `plot/plotly-json` | `reuse_with_adapter` | Replace with runtime artifact contract or keep as one renderer plugin. |
| `src/components/settings/WidgetAccountSettings.tsx` | Large settings/account/tools/skills overlay | lucide, spinner, widget settings | Uses local `DEFAULT_TOOLS`, `DEFAULT_SKILLS`, data analyst runtime settings | `rewrite` | Visual patterns can inspire panels, but logic/data should come from backend endpoints. Shell output showed mojibake labels, so copy with care. |
| `src/chat/useWidgetChatAgent.ts` | Chat state hook and stream event reducer | React, widget runtime, widget types | Widget event taxonomy and final payload | `rewrite` | Keep the architectural idea, not implementation. Runtime needs typed reducer for `RuntimeEvent`. |
| `src/chat/widget-chat-runtime.ts` | Selects mock vs backend runtime | Widget config | `mode: mock/backend` | `rewrite` | Replace with runtime API client mode/fake-provider test adapter. |
| `src/chat/backend-chat-runtime.ts` | Auth, backend session, SSE parser | fetch, widget config/types | `/auth/luxms/otp-login`, `/sessions`, `/sessions/{id}/query/stream`, `/runtime/model` | `rewrite` | SSE parser logic is reusable, but endpoint/auth/request/event mapping is incompatible. |
| `src/chat/mock-chat-runtime.ts` | Deterministic visual demo stream | widget types | Mock data analyst tools/artifacts | `reuse_with_adapter` | Keep as a storybook/dev-fixture idea. Replace event names with runtime fixtures. |
| `src/types/backend-types.ts` | Widget API/event/message/artifact types | TypeScript only | Data analyst backend response shapes | `rewrite` | Replace with generated or hand-maintained `langgraph-agent-blueprint` DTO/event types. |
| `src/config/widget-config.ts` | Browser global config reader | `window.__LLM_ANALYST_WIDGET_DEV__` | `apiBaseUrl`, Luxms identity | `rewrite` | Use Vite env/runtime config for current backend. Do not keep Luxms-specific shape. |
| `src/settings/widget-chat-settings.ts` | Local display/runtime settings | TypeScript only | Data analyst `analysisDepth`, selected SQL/Plotly skills | `reuse_with_adapter` | Keep display options; remove backend runtime knobs unless backed by config API. |
| `src/styles.css` | Tailwind v4 import, theme tokens, markdown, animations | Tailwind v4, Google fonts | None | `reuse_with_adapter` | Strong visual base. Remove external font import if offline/security policy requires bundled/system fonts. |
| `src/main.tsx` | Vite entrypoint | ReactDOM | None | `reuse_with_adapter` | Main project currently uses React 19/JS; decide whether to migrate to TS and align versions. |
| `vite.config.ts` | Vite + React + Tailwind + Vitest jsdom config | Vite, Tailwind plugin | None | `reuse_with_adapter` | Good if main frontend migrates to TS/Vitest. Current frontend uses Vite 7 and no TS. |
| `tsconfig.json` | Strict TS config | TypeScript | None | `reuse_as_is` | Good baseline for migration. |
| `tests/widget-backend-connection.test.ts` | Backend adapter contract tests | Vitest, fetch stubs | Luxms/session/query stream API | `reuse_with_adapter` | Rewrite around `/chat`, `/chat/stream`, `/approval`, registry/status endpoints. |
| `tests/widget-contract.test.tsx` | Artifact, spinner, mock runtime, forbidden token tests | Testing Library, fs | Widget event/artifact contract | `reuse_with_adapter` | Useful pattern for frontend contract tests. |
| `tests/widget-chat-ui.test.tsx` | Chat UI behavior tests | Testing Library/user-event | Widget mock stream and settings labels | `reuse_with_adapter` | Keep style of behavioral tests; rewrite assertions around runtime UI. |

## Inventory Summary

Best reuse candidates:

- `WidgetChatPanel` layout after API replacement.
- `WidgetComposer` after context/attachments support.
- `WidgetMessageList` and `WidgetMessageBubble`.
- `WidgetActivityFeed` as the starting point for a runtime event timeline.
- `WidgetMarkdownBlock`.
- `WidgetSpinnerDisplay`.
- CSS theme tokens and markdown styles.
- Vitest/Testing Library test style.

Highest rewrite candidates:

- `backend-chat-runtime.ts`.
- `useWidgetChatAgent.ts`.
- `backend-types.ts`.
- `widget-config.ts`.
- `WidgetAccountSettings.tsx`.

Discard or postpone:

- Luxms auth flow.
- Data analyst specific artifacts unless runtime adopts compatible artifacts.
- Local mock SQL/Plotly/planner tool registry.
- Disabled export button behavior.

