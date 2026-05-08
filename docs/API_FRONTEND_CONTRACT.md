# API Frontend Contract

Audit date: 2026-05-08
Last contract update: 2026-05-08

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
| GET | `/sessions/{session_id}/events` | `get_session_events` |
| GET | `/sessions/{session_id}/messages` | `get_session_messages` |
| GET | `/sessions/{session_id}/context` | `get_session_context` |
| GET | `/sessions/{session_id}/child-runs` | `list_child_runs` |
| GET | `/sessions/{session_id}/child-runs/{child_run_id}` | `get_child_run` |
| POST | `/sessions/{session_id}/export` | `export_session` |
| GET | `/commands` | `list_commands` |
| GET | `/skills` | `list_skills` |
| GET | `/tools` | `list_tools` |
| GET | `/mcp` | `list_mcp` |
| GET | `/plugins` | `get_plugins_status` |
| GET | `/hooks` | `get_hooks_status` |
| GET | `/config` | `get_config` |
| GET | `/config/explain` | `explain_config` |
| GET | `/config/validate` | `validate_config` |
| GET | `/observability` | `get_observability_status` |
| GET | `/docs` | FastAPI docs |
| GET | `/openapi.json` | OpenAPI |
| GET | `/redoc` | ReDoc |

Note: `/commands`, `/skills`, and `/tools` are now router-owned only. OpenAPI exposes one operation per path/method.

## Core Chat

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Send message | yes | `POST /chat` | `ChatRequest(message, session_id?, thread_id?, attachments[])` | `ChatResponse(session_id, thread_id, final_response?, events, permission_required?)` | no | working | None for basic MVP. | P1 |
| Stream chat events live | yes | `POST /chat/stream` | `ChatRequest` | SSE frames containing `StreamFrame` with `RuntimeEventDTO` | live SSE | working | TypeScript SSE parser/client still needed in frontend. | P1 |
| Resume after approval | yes | `POST /approval` | `ApprovalRequest(thread_id, session_id?, decision: PermissionDecisionDTO)` | `ChatResponse` | no | working | Legacy `{approved}` shape remains supported for the old shell. | P1 |
| Reject permission | yes | `POST /approval` | same | same | no | working | `permission_resolved` event is returned in response events. | P1 |
| Get final response | yes | `POST /chat`, `POST /approval` | same | `final_response` | no | working | None. | P1 |
| Get current run/session state | yes | `GET /sessions/{session_id}` | path id | `SessionDetailDTO` | no | working | Pending approval is still delivered through chat/stream response, not session detail. | P1 |

## Sessions

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Create session | implicit | `POST /chat` | no explicit create DTO | `session_id` in response | no | partial | Optional `POST /sessions` for empty session creation. | P2 |
| List sessions | yes | `GET /sessions` | none | `list[SessionListItemDTO]` | no | working | None. | P1 |
| Resume session | partial | CLI and slash `/resume`; API can pass `session_id` to `/chat` | `ChatRequest.session_id` | `ChatResponse` | no | partial | Add `POST /sessions/{id}/resume` or document `/chat` resume semantics. | P1 |
| Clear session | missing | none | n/a | n/a | n/a | missing | Add clear endpoint or command invocation API. | P2 |
| Export transcript | yes | `POST /sessions/{id}/export` | `ExportRequest(format)` | `ExportRecordDTO` | no | working | Download/read endpoint is still deferred. | P1 |
| Get session events | yes | `GET /sessions/{id}/events` | path id | `list[RuntimeEventDTO]` | no | working | Pagination/filtering can be added later. | P1 |
| Get session messages | yes | `GET /sessions/{id}/messages` | path id | `list[MessageDTO]` | no | working | None. | P1 |
| Get child/subagent runs | yes | `GET /sessions/{id}/child-runs`, `GET /sessions/{id}/child-runs/{child_run_id}` | path ids | `ChildRunListItemDTO`, `ChildRunDetailDTO` | no | working | Child transcript UI still not implemented. | P1 |

## Runtime Surfaces

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| List tools | yes | `GET /tools` | none | `ToolRegistryDTO` | no | working | None. | P1 |
| List skills | yes | `GET /skills` | none | `SkillRegistryDTO` | no | working | None. | P1 |
| List commands | yes | `GET /commands` | none | `CommandRegistryDTO` | no | working | None. | P1 |
| List plugins | yes | `GET /plugins` | none | `PluginStatusDTO` | no | working | Install/update/remove remain deferred. | P1 |
| List hooks | yes | `GET /hooks` | none | `HookStatusDTO` | no | working | None for read-only panel. | P2 |
| List MCP servers/tools/resources/prompts | yes | `GET /mcp` | none | discovery dict | no | working | Consider separate endpoints and avoid starting discovery unexpectedly in panel refresh. | P1 |
| List context refs/fragments | yes | `GET /sessions/{id}/context` | path id | `ContextStateDTO` | no | working | Upload/file-picker endpoint remains future work. | P1 |
| List memory | partial | slash `/memory`; storage has memory refs | no direct API | command text/raw session | no | partial | Add `GET /sessions/{id}/memory` or `GET /memory?scope=...`. | P2 |
| List todos | partial | slash `/todo`; storage session has todos | no direct API | command text/raw session | no | partial | Add `GET /sessions/{id}/todos`. | P2 |
| Observability status | yes | `GET /observability` | none | `ObservabilityStatusDTO` | no | working | None for read-only panel. | P2 |
| Config show/explain/validate | yes | `GET /config`, `GET /config/explain`, `GET /config/validate` | none | `ConfigShowDTO`, `ConfigExplainDTO`, `ConfigValidateDTO` | no | working | Config editing is intentionally deferred. | P1 |
| Eval list/run/report | partial | CLI `eval ...` | no API | CLI/report files | no | future | Keep CLI-only for frontend MVP; add later if dashboard is desired. | P3 |

## Actions

| Frontend need | Endpoint exists | Method/path | Request schema | Response schema | Streaming | Status | Missing work | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Invoke slash command | partial | `POST /chat` with message starting `/` | `ChatRequest.message` | `ChatResponse` | no | partial | Acceptable for MVP; optional `POST /commands/{name}` for command-specific UX. | P2 |
| Approve/reject permission | yes | `POST /approval` | `PermissionDecisionDTO` or legacy `{approved}` | `ChatResponse` | no | working | None for MVP. | P1 |
| Install/remove/update plugin | missing API | CLI only | n/a | n/a | n/a | missing | Add guarded plugin management endpoints only after UI trust policy is designed. | P2 |
| Run eval scenario | missing API | CLI only | n/a | n/a | n/a | future | Defer dashboard until after chat/session frontend. | P3 |
| Attach context/file | partial | `POST /chat` accepts `attachments[]`; `@mentions` in message | `AttachmentRef[]` | context events in response | no | partial | Add upload/file picker integration endpoint later. | P1 |
| Request MCP resource context | partial | `@mcp:<server>:<uri>` through chat input | message text | context events | no | partial | Add MCP resource browser first, then insert `@mcp` refs into chat. | P2 |
| Trigger export | yes | `POST /sessions/{id}/export` | `ExportRequest` | `ExportRecordDTO` | no | working | Download response is deferred. | P1 |
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

- `ApprovalRequest.decision` now accepts `PermissionDecisionDTO(tool_call_id, decision, reason?, remember?)`.
- The old frontend `{approved, reason}` shape remains accepted for compatibility, but the next typed frontend should send `tool_call_id`.
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
| Budget panel | yes | `GET /sessions/{id}/context` | yes | budget visualization | working |
| Trust markers | yes | event/session payloads | yes | render badges/warnings | working |
| Upload endpoint | no | n/a | n/a | upload/file picker backend | missing |

## Sessions, Subagents, Export

Sessions are usable through API for list/detail and through chat for resume-like behavior. Current frontend-facing DTOs include:

- session list item
- session detail
- normalized messages
- event list
- tool call list
- todos/memory
- child run refs

Subagent runtime is working, and events include `child_run_id` plus parent/child ids. Frontend-facing endpoints now provide child run list/detail, child event transcript, and result summary.

Export exists through slash command, service, and `POST /sessions/{session_id}/export`. Still deferred:

- list export artifacts
- download/read export artifact

## Plugins / MCP / Hooks / Config Panels

| Panel | Backend data source | Direct API | Status | Notes |
| --- | --- | --- | --- | --- |
| Plugins | `PluginService.discover`, slash `/plugins`, CLI plugin commands | `GET /plugins` | working | Install/update/remove remain deferred behind trust UX. |
| MCP | `GET /mcp` | yes | working | Discovery may start stdio processes; document panel refresh behavior. |
| Hooks | hook registry, slash `/hooks` | `GET /hooks` | working | Read-only registry snapshot. |
| Config | `AppConfig.load_with_report`, CLI/slash commands | `GET /config`, `/config/explain`, `/config/validate` | working | Read-only/redacted. |
| Observability | `ObservabilityService.status`, slash `/observability`, `/doctor` | `GET /observability` | working | Read-only/redacted. |

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
| TypeScript frontend API client and stream parser | must_fix_before_frontend_ui | Backend now exposes SSE; frontend still needs parser/reducer code. |
| Upload/download endpoints | nice_to_have | Required for richer attachments/export UX, not basic `@mention` chat. |
| Plugin install/update/remove endpoints | future | Needs explicit trust UX; not required for MVP. |
| Eval endpoints | future | CLI-only is acceptable for MVP. |
