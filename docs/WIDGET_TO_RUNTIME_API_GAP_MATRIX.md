# Widget To Runtime API Gap Matrix

Date: 2026-05-08

This matrix compares the external widget's API assumptions with the current `langgraph-agent-blueprint` backend/API contract.

Compatibility values:

- `yes`: usable with little or no adapter.
- `partial`: concept maps, but shape or behavior differs.
- `no`: incompatible without backend or frontend adapter work.
- `not_present`: widget does not currently model the need.

| Widget need/API call | Widget expected shape | Current langgraph endpoint | Current shape | Compatible? | Needed adapter/change | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Backend mode config | `window.__LLM_ANALYST_WIDGET_DEV__.mode/apiBaseUrl/luxmsIdentity` | Current frontend uses `VITE_API_BASE_URL` | No typed runtime config endpoint for frontend bootstrap | partial | Replace browser global Luxms config with typed runtime frontend config. | P1 |
| Auth | POST `/auth/luxms/otp-login`, bearer token | None in current API | Local/dev API currently has no auth layer | no | Remove old Luxms auth. Add future auth adapter only if needed. | P2 |
| Create session | POST `/sessions` returns `{session_id}` | GET `/sessions`; session created by `/chat` invoke | `ChatResponse` returns `session_id` and `thread_id` | partial | Let `/chat` create session, or add explicit create-session endpoint if UI needs it. | P1 |
| Send message | POST `/sessions/{session_id}/query/stream` | POST `/chat` | `{message, session_id?, thread_id?, attachments[]}` -> `{session_id, thread_id, final_response, events, permission_required}` | no | New client method for `/chat`; map widget prompt to `message`. | P0 |
| Stream message | SSE from `/sessions/{id}/query/stream` | POST `/chat/stream` | Returns `list[dict]`, not live SSE/NDJSON/WebSocket | no | Backend needs live streaming endpoint, or frontend initially treats batch list as pseudo-stream. | P0 |
| Stream event envelope | SSE `event: token/final/tool_start/...` with data body | Runtime events in `events[]` or stream list | `{id,type,timestamp,session_id,node,severity,data}` | no | Replace event parser/reducer with runtime event envelope parser. | P0 |
| Final response | `final` event payload `{text, artifacts, metrics}` | `ChatResponse.final_response`; `final_response` event | Text plus runtime events | partial | Build assistant message from response and final event. Runtime artifacts need separate contract. | P0 |
| Token streaming | `token` events | `model_token` events may exist, but `/chat/stream` is batch-list | Runtime event data shape differs | partial | Map `model_token` to draft; live endpoint needed for real token UX. | P1 |
| Reasoning/thinking | `reasoning`, `reasoning_token`, `thinking_start/end` | No equivalent stable frontend contract in readiness docs except model/runtime events | Runtime may emit model/tool events, not old thinking blocks | partial | Treat as optional event group; do not require old reasoning fields. | P2 |
| Tool activity | `tool_start`, `tool_end` with `tool_name`, summaries/previews | `tool_call_started`, `tool_call_finished`, `tool_call_error` | Runtime event data includes tool call info | partial | Map runtime tool events into generic activity feed rows. | P0 |
| Permission approval | Not implemented | POST `/approval`; POST `/approval/events` | `ApprovalRequest(thread_id, session_id?, decision)` | no | Add permission modal/bar and preserve session/thread ids. | P0 |
| Permission event | Not implemented | `permission_required`, `permission_resolved` | Runtime events and `ChatResponse.permission_required` | no | Add typed permission view model and approve/reject client methods. | P0 |
| Session list | Widget caches one backend session in memory | GET `/sessions` | `list[dict]` from storage service | partial | Add typed session list DTO for frontend. | P1 |
| Session detail/history | Widget stores messages locally | GET `/sessions/{session_id}` | Raw persisted session dict | partial | Add typed session detail/messages/events endpoint or adapter. | P1 |
| Export | Disabled button only | Slash command/runtime export exists; no direct endpoint in readiness audit | Event/storage based | no | Add export endpoint/download flow before UI export. | P2 |
| Attachments | Not implemented | `ChatRequest.attachments: AttachmentRef[]` | Minimal API field exists | partial | Add composer/file/text attachment UI and typed client. | P1 |
| @mentions/context refs | Not implemented | Runtime parses prompt; context events emitted | Context provider layer exists | partial | Add @mention composer support and context side panel. | P1 |
| Context budget/trust | Not implemented | Runtime context events and budget report | Mostly event/session metadata, no dedicated endpoint noted | partial | Add event renderer and probably `/context` endpoint. | P1 |
| Tools registry | Local mock tools in settings overlay | GET `/tools` | Registry snapshot | partial | Replace local constants with backend snapshot; handle duplicate route cleanup. | P1 |
| Skills registry | Local mock skills in settings overlay | GET `/skills` | Registry snapshot | partial | Replace local constants; support `/skill` routes via chat/command. | P1 |
| Commands registry | Not modeled in widget | GET `/commands` | Registry snapshot | partial | Add command palette/hints from backend. | P1 |
| Slash command execution | Not modeled | Through `/chat` message path | Commands handled by graph/runtime | partial | Send slash text through chat; optionally add command endpoint later. | P2 |
| Plugins panel | Not modeled | Mostly CLI/slash commands; no direct endpoint in readiness audit | Plugin registry available in runtime, not frontend-facing enough | no | Add frontend-facing plugin status/diagnostics endpoints before panel. | P2 |
| MCP panel | Not modeled | GET `/mcp` | MCP snapshot | partial | Add typed DTO and UI list/status; resource browser later. | P2 |
| Hooks panel | Not modeled | CLI/slash currently | No direct endpoint noted | no | Add hooks status endpoint if frontend panel is MVP. | P2 |
| Config panel | Widget settings are local | CLI/slash config commands | No direct config endpoint noted | no | Add `config show/explain/validate` API endpoints or keep CLI-only initially. | P2 |
| Observability panel | Not modeled | CLI/slash observability | No direct endpoint noted | no | Add observability status endpoint before panel. | P2 |
| Eval panel | Not modeled | CLI eval commands | No direct endpoint noted | no | Keep CLI-only for frontend MVP or add eval endpoints later. | P3 |
| Subagents | Not modeled | Runtime subagent events | `subagent_started/event/finished/error/...` | partial | Add timeline rendering and child-run detail endpoint later. | P1 |
| MCP events | Not modeled | Runtime MCP events | Many event types in runtime contract | partial | Generic event renderer can show now; richer panel later. | P2 |
| Hook events | Not modeled | Runtime hook events | Hook event types in runtime contract | partial | Generic event renderer can show now. | P2 |
| Artifact rendering | Table/json/value/plot payloads | Runtime artifact contract not clearly frontend-facing yet | Artifact refs/results may differ by tool | partial | Keep renderer behind adapter for compatible artifacts; define runtime artifact DTO first. | P2 |
| Model label | GET `/runtime/model` | No equivalent endpoint noted | Config/doctor can report provider/model via CLI | no | Add lightweight status/model endpoint or include in config/status response. | P2 |

## Critical API Gaps Before Widget Migration

1. Live streaming: widget is built for streamed events, but current `/chat/stream` returns a list after graph execution.
2. Runtime event types: widget needs a new `RuntimeEvent` parser/reducer, not a patch to old `WidgetStreamEvent`.
3. Permission UX: widget has no approval UI and no `/approval` integration.
4. Session DTOs: widget keeps session state locally; runtime needs typed list/detail/message/event DTOs.
5. Context/attachments: runtime supports them, widget does not render or configure them.
6. Extension panels: plugins, hooks, MCP, config, observability, eval are not represented in widget UI.
7. Old auth and Luxms endpoints must be removed from the main runtime frontend path.

## Compatibility Conclusion

The widget is not API-compatible with `langgraph-agent-blueprint`. It is still valuable because it already solves many presentation problems: streaming draft UX, message layout, tool rows, markdown, artifact chips, settings surface, and frontend tests. The migration should replace the integration layer first, then port selected presentation components.

