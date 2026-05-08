# API Frontend Contract

Audit date: 2026-05-08

This document maps frontend needs to the current FastAPI contract. Status values:

- `working`: endpoint exists and matches the frontend need.
- `partial`: some backend/API support exists, but the contract is incomplete for a normal UI.
- `missing`: no direct API endpoint.
- `not_needed_for_frontend_mvp`: reasonable to defer.
- `future`: should not block MVP.

## Current Route Inventory

Observed routes from `create_app(AppConfig(llm_provider="fake"))`:

| Method | Path | Handler |
| --- | --- | --- |
| POST | `/chat` | `chat` |
| POST | `/chat/stream` | `chat_stream` |
| POST | `/approval` | `approval` |
| POST | `/approval/events` | `approval_events` |
| GET | `/sessions` | `list_sessions` |
| GET | `/sessions/{session_id}` | `get_session` |
| GET | `/commands` | `commands`, `list_commands` |
| GET | `/skills` | `skills`, `list_skills` |
| GET | `/tools` | `tools`, `list_tools` |
| GET | `/mcp` | `list_mcp` |
| GET | `/docs` | FastAPI docs |
| GET | `/openapi.json` | OpenAPI |
| GET | `/redoc` | ReDoc |

Note: `/commands`, `/skills`, and `/tools` are each defined twice: once inline in `server.py` and once through included routers. This should be cleaned before relying on OpenAPI generation.

## Core Chat

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Send message | yes | `POST /chat` | `ChatRequest(message, session_id?, thread_id?, attachments[])` | `ChatResponse(session_id, thread_id, final_response?, events, permission_required?)` | no | working | None for basic MVP. | P1 |
| Stream chat events live | partial | `POST /chat/stream` | `ChatRequest` | `list[RuntimeEvent dict]` | batch list, not live | partial | Add SSE, chunked NDJSON, or WebSocket stream with stable framing. | P1 |
| Resume after approval | yes | `POST /approval` | `ApprovalRequest(thread_id, session_id?, decision)` | `ChatResponse` | no | working | Make `decision` a typed DTO instead of raw dict. | P1 |
| Reject permission | yes | `POST /approval` | same | same | no | working | Include approval/rejection event in response consistently. | P1 |
| Get final response | yes | `POST /chat`, `POST /approval` | same | `final_response` | no | working | None. | P1 |
| Get current run/session state | partial | `GET /sessions/{session_id}` | path id | raw storage dict | no | partial | Add frontend DTO for current run state and latest pending approval. | P1 |

## Sessions

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Create session | implicit | `POST /chat` | no explicit create DTO | `session_id` in response | no | partial | Optional `POST /sessions` for empty session creation. | P2 |
| List sessions | yes | `GET /sessions` | none | `list[dict]` metadata | no | working | Add typed `SessionListItem` response. | P1 |
| Resume session | partial | CLI and slash `/resume`; API can pass `session_id` to `/chat` | `ChatRequest.session_id` | `ChatResponse` | no | partial | Add `POST /sessions/{id}/resume` or document `/chat` resume semantics. | P1 |
| Clear session | missing | none | n/a | n/a | n/a | missing | Add clear endpoint or command invocation API. | P2 |
| Export transcript | partial | slash `/export`; storage export service exists | no direct API | command response only | no | partial | Add `POST /sessions/{id}/export` and download/read endpoint. | P1 |
| Get session events | partial | `GET /sessions/{id}` | path id | raw `events` list | no | partial | Add typed event page/filter endpoint. | P1 |
| Get session messages | partial | `GET /sessions/{id}` | path id | raw message objects | no | partial | Normalize LangChain messages into frontend DTOs. | P1 |
| Get child/subagent runs | partial | child refs in storage metadata; child files persisted | no direct API | raw session only | no | partial | Add `GET /sessions/{id}/child-runs` and `GET /sessions/{id}/child-runs/{child_run_id}`. | P1 |

## Runtime Surfaces

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| List tools | yes | `GET /tools` | none | registry snapshot dict | no | working | Type response and remove duplicate route. | P1 |
| List skills | yes | `GET /skills` | none | registry snapshot dict | no | working | Type response and remove duplicate route. | P1 |
| List commands | yes | `GET /commands` | none | registry snapshot dict | no | working | Type response and remove duplicate route. | P1 |
| List plugins | partial | slash `/plugins`, CLI `plugins list` | no API | command text/CLI JSON | no | partial | Add `GET /plugins` with diagnostics/contribution counts/trust. | P1 |
| List hooks | partial | slash `/hooks` | no API | command text | no | partial | Add `GET /hooks`. | P2 |
| List MCP servers/tools/resources/prompts | yes | `GET /mcp` | none | discovery dict | no | working | Consider separate endpoints and avoid starting discovery unexpectedly in panel refresh. | P1 |
| List context refs/fragments | partial | slash `/context`; session state has fields | no direct API | command text/raw session | no | partial | Add `GET /sessions/{id}/context`. | P1 |
| List memory | partial | slash `/memory`; storage has memory refs | no direct API | command text/raw session | no | partial | Add `GET /sessions/{id}/memory` or `GET /memory?scope=...`. | P2 |
| List todos | partial | slash `/todo`; storage session has todos | no direct API | command text/raw session | no | partial | Add `GET /sessions/{id}/todos`. | P2 |
| Observability status | partial | slash `/observability`, `/doctor` includes status | no API | command text | no | partial | Add `GET /observability`. | P2 |
| Config show/explain/validate | partial | CLI `config ...`, slash `/config ...` | no API | command text/CLI text | no | partial | Add `GET /config`, `GET /config/explain`, `POST /config/validate` or equivalent. | P1 |
| Eval list/run/report | partial | CLI `eval ...` | no API | CLI/report files | no | future | Keep CLI-only for frontend MVP; add later if dashboard is desired. | P3 |

## Actions

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Invoke slash command | partial | `POST /chat` with message starting `/` | `ChatRequest.message` | `ChatResponse` | no | partial | Acceptable for MVP; optional `POST /commands/{name}` for command-specific UX. | P2 |
| Approve/reject permission | yes | `POST /approval` | raw `decision` dict | `ChatResponse` | no | working | Type the decision schema and include `tool_call_id` in frontend request. | P1 |
| Install/remove/update plugin | missing API | CLI only | n/a | n/a | n/a | missing | Add guarded plugin management endpoints only after UI trust policy is designed. | P2 |
| Run eval scenario | missing API | CLI only | n/a | n/a | n/a | future | Defer dashboard until after chat/session frontend. | P3 |
| Attach context/file | partial | `POST /chat` accepts `attachments[]`; `@mentions` in message | `AttachmentRef[]` | context events in response | no | partial | Add upload/file picker integration endpoint later. | P1 |
| Request MCP resource context | partial | `@mcp:<server>:<uri>` through chat input | message text | context events | no | partial | Add MCP resource browser first, then insert `@mcp` refs into chat. | P2 |
| Trigger export | partial | slash `/export` through `/chat` | message text | final response with path | no | partial | Add export endpoint and download response. | P1 |
| Trigger compact | partial | slash `/compact` through `/chat` | message text | events/final response | no | partial | Accept command path for MVP. | P2 |
| Clear context | partial | slash `/context clear` through `/chat` | message text | events/final response | no | partial | Add direct context endpoint if panel needs stateful clear. | P2 |

## Approval UX Readiness

Status: ready with caveats.

Backend provides:

- `permission_required` interrupt payload in `ChatResponse.permission_required`.
- `tool_call_id`, `tool_name`, `action`, `risk`, `args_summary`, `reason`, `args`.
- `thread_id` and `session_id` in `ChatResponse`.
- `POST /approval` resumes the LangGraph checkpoint and preserves `session_id` when provided.
- API tests cover approval/rejection and Langfuse session id propagation.

Caveats:

- `ApprovalRequest.decision` is `dict[str, Any]`, not `PermissionDecision`.
- Current frontend sends `{approved, reason}` and omits `tool_call_id`; runtime adapts this, but a typed frontend should send the explicit decision contract.
- Nested subagent approval is intentionally limited. Child side-effect approvals return structured subagent errors rather than silently executing.

## Context / Attachments Readiness

| Context feature | Backend support | API support | Event support | UI requirement | Status |
| --- | --- | --- | --- | --- | --- |
| `@file` refs | yes | message text | yes | autocomplete/preview | working |
| `@directory` refs | yes | message text | yes | tree preview | working |
| `@glob` refs | yes | message text | yes | pattern input/result preview | working |
| notebooks | yes | message text | yes | notebook summary UI | working |
| MCP resources | yes | message text | yes | MCP resource selector | partial |
| URL context | guarded | message text | yes | URL input and error display | partial |
| Pasted text/text attachments | model exists | `attachments[]` | yes | paste/drop UI | partial |
| Image/PDF records | metadata placeholder | `attachments[]` | limited | metadata-only UI | partial |
| Budget panel | yes | raw events/session state | yes | budget visualization | partial |
| Trust markers | yes | event/session payloads | yes | render badges/warnings | working |
| Upload endpoint | no | n/a | n/a | upload/file picker backend | missing |

## Sessions, Subagents, Export

Sessions are usable through API for list/detail and through chat for resume-like behavior, but the frontend needs typed DTOs for:

- session list item
- session detail
- normalized messages
- event list
- tool call list
- todos/memory
- child run refs

Subagent runtime is working, and events include `child_run_id` plus parent/child ids. Missing frontend-facing endpoints:

- child run list
- child run detail
- child event transcript
- child result summary

Export exists through slash command and service. Missing frontend-facing endpoints:

- trigger export for a session
- list export artifacts
- download/read export artifact

## Plugins / MCP / Hooks / Config Panels

| Panel | Backend data source | Direct API | Status | Notes |
| --- | --- | --- | --- | --- |
| Plugins | `PluginService.discover`, slash `/plugins`, CLI plugin commands | no | partial | Add read-only `GET /plugins` before install/update UI. |
| MCP | `GET /mcp` | yes | working | Discovery may start stdio processes; document panel refresh behavior. |
| Hooks | hook registry, slash `/hooks` | no | partial | Add `GET /hooks`. |
| Config | `AppConfig.load_with_report`, CLI/slash commands | no | partial | Add config endpoints with redaction and diagnostics. |
| Observability | `ObservabilityService.status`, slash `/observability`, `/doctor` | no | partial | Add `GET /observability`. |

## Eval / Replay UI Recommendation

Eval/replay should remain CLI-only for the first frontend MVP. It is valuable for development and regression, but not required for the operational chat UI. A later dashboard can expose:

- scenario list
- run one/all
- report list/detail
- pass/fail summaries
- event/tool/context/subagent counters

Do not block chat/session frontend on eval endpoints.

## Backend Gaps Before Frontend

| Gap | Classification | Rationale |
| --- | --- | --- |
| Real streaming transport | must_fix_before_frontend | Live event timeline and token streaming require SSE/NDJSON/WebSocket. |
| Remove duplicate `/commands`, `/skills`, `/tools` routes | must_fix_before_frontend | Duplicate route definitions make OpenAPI and typed client generation fragile. |
| Typed event/API schemas for frontend | must_fix_before_frontend | Frontend should not grow around ad hoc `dict` payloads. |
| Session detail DTO | must_fix_before_frontend | Raw storage shape is not stable UI contract. |
| Config/plugin/hook/observability read-only endpoints | nice_to_have | Frontend can start with chat/session but side panels need these. |
| Plugin install/update/remove endpoints | future | Needs explicit trust UX; not required for MVP. |
| Eval endpoints | future | CLI-only is acceptable for MVP. |
| Upload/download endpoints | nice_to_have | Required for richer attachments/export UX, not basic `@mention` chat. |

