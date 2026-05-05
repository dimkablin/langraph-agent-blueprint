# Fix Plan

## Implementation Status (2026-05-06)

P0 and P1 items in this plan have been implemented and covered by passing regression tests:

- state/event reducers
- provider system context and tool binding
- `ToolMessage` feedback in the model loop
- default `project_root` fix
- permission events/decision persistence
- skill graph routing and allowed-tools enforcement
- `/compact`, `/export`, `/resume`, `/doctor`
- command output depth for `/skills`, `/status`, `/cost`, `/config`, `/memory`, `/todo`
- Windows `grep` path parsing
- PowerShell execution
- web search unavailable status without provider
- session metadata merge/restore
- stream-json event streaming

Remaining P2 limitations are documented disabled/limited:

- full MCP server lifecycle
- full plugin contribution wiring
- real child graph subagents
- provider-specific cost accounting

See `docs/FIX_IMPLEMENTATION_LOG.md` for files changed, tests, and runtime smoke evidence.

This plan is ordered by runtime blast radius. P0 items block most tools/skills.

## P0 Fixes

| Priority | Affected capabilities | Root cause | Files to change | Concrete code change | Required tests | Expected result | Risk | Blocking many features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | All real-provider tools/skills | Providers ignore `system_context` and `tools`. | `services/model_provider.py`, `models/llm.py`, `models/prompts.py` | Add `SystemMessage`; convert internal tool schemas to LangChain tools; call `bind_tools` where supported. | Provider fake and mocked LangChain tool-binding tests; optional Ollama manual test. | Ollama/Qwen can emit `pending_tool_calls`. | Medium: provider-specific schema differences. | yes |
| P0 | Tool loop, final answers | Tool results are not returned as `ToolMessage`. | `graph/nodes/model_call.py`, `tool_executor.py`, state/messages schemas | Preserve assistant tool-call message and append `ToolMessage(tool_call_id=...)` after execution. | E2E fake-provider and mocked provider tests asserting message sequence. | Model sees tool result and can produce final answer. | Medium. | yes |
| P0 | CLI/API/frontend events, persistence | `ui_events` overwritten. | `graph/state.py`, nodes returning events, storage tests | Add reducer for event append; make nodes return deltas. | Runtime tests requiring tool_call_started/finished and command events in final API. | Frontend sees tool/skill/progress events. | Low/medium: event duplication possible. | yes |
| P0 | File/search/shell tools | Default project root becomes `storage_dir`. | `dependencies.py`, `cli.py`, `api/server.py`, tests | Use `Path.cwd()` or explicit project root as default; keep storage separate. | Test default `project_root != storage_dir`; CLI/API config test. | Tools operate in workspace, not `.storage`. | Medium: existing storage hashing paths change. | yes |
| P0 | Skills | Skill runtime is prompt expansion only; allowed tools not enforced. | `graph/subgraphs/skill_graph.py`, `graph/nodes/skill_router.py`, `tool_router.py`, `services/skill_service.py` | Build real skill subgraph: resolve -> emit event -> apply allowed tool scope -> model/tool loop -> merge result -> persist invocation. | `/skill verify` can request shell via fake/mocked provider; allowed disallowed tool is rejected. | Skills become functional runtime capabilities. | Medium/high. | yes |
| P0 | Permission flow UX/events | Resume decisions/events are overwritten and not persisted. | `permission_gate.py`, `state.py`, `persist_session.py` | Append `permission_decisions`; persist decisions; emit visible `permission_resolved`. | Approval/rejection API tests assert events and persistence. | Human-in-loop visible and durable. | Low. | yes |

## P1 Fixes

| Priority | Affected capabilities | Root cause | Files to change | Concrete code change | Required tests | Expected result | Risk | Blocking many features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | `grep` | Windows `C:\...` path parsing. | `services/search_service.py` | Use `rg --json` or parse from right around line number. | Windows path grep test. | `grep` works in project root. | Low. | no |
| P1 | `/compact` | Manual flag not surfaced correctly; command proceeds to model. | `commands/builtin.py`, `routing.py`, `compact_decision.py`, `compact_context.py` | Route manual compact directly to compaction; respect `compact_requested`; return summary. | `/compact` E2E test. | Manual compaction produces summary and events. | Medium. | no |
| P1 | `/export` | Command only sets metadata. | `command_router.py`, `commands/builtin.py`, `services/export_service.py`, storage | Execute export service and add `exported_outputs`. | `/export` creates file test. | Transcript export works from command/API. | Low. | no |
| P1 | `/resume` and sessions | Session command does not restore graph state. | `graph/subgraphs/session_lifecycle_graph.py`, `builder.py`, `session_service.py`, CLI/API | Load messages/todos/memory/tool refs into initial state. | Resume then continue chat test. | Session continuation works. | Medium/high. | yes for long-running sessions |
| P1 | `/doctor` | Not wired to diagnostics. | `commands/builtin.py`, `services/diagnostics_service.py` | Return actual diagnostics result. | `/doctor` command test. | User sees provider/root/registry issues. | Low. | no |
| P1 | `web_search` | No provider; returns empty success. | `services/web_service.py`, config, docs | Add disabled/unavailable status unless provider configured. | Network false/true no-provider tests. | No false claim that web search works. | Low. | no |
| P1 | Notebook editing | No E2E approval test. | tests first, maybe notebook service | Add fake-provider approval test; fix if needed. | Notebook edit E2E. | Status known/proven. | Low. | no |
| P1 | CLI stream-json | Not true streaming; Rich/Windows encoding can crash on Unicode. | `cli.py`, `graph/streaming.py` | Use plain `print`/UTF-8 safe output and LangGraph streaming. | Unicode stream-json test. | Machine-readable stream works. | Low. | no |

## P2 Fixes

| Priority | Affected capabilities | Root cause | Files to change | Concrete code change | Required tests | Expected result | Risk | Blocking many features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2 | Plugins | Manifest discovery not wired to registries. | `dependencies.py`, `plugin_service.py`, registries | Register plugin commands/skills/tools/hooks. | Plugin manifest integration test. | Plugin contributions visible/executable. | Medium. | no |
| P2 | MCP | Only mock/discovery abstraction. | `mcp_service.py`, `mcp_graph.py`, tools | Implement server lifecycle/tool invocation or mark disabled. | Mock and no-config tests. | Clear MCP status. | Medium/high. | no |
| P2 | Subagents | Synthetic child result. | `agent_service.py`, `agent_graph.py` | Run child compiled graph with forked state. | Child graph E2E. | Real subagent execution. | Medium/high. | no |
| P2 | Usage/cost | Fake token estimates and no cost. | `usage_service.py`, providers, `/cost` | Capture provider usage where available; aggregate by session. | `/cost` after query. | Honest usage/cost status. | Low/medium. | no |
| P2 | Optional commands | Placeholders shown as active. | command registry/docs | Hide, disable, or implement. | `/help` enabled/disabled split. | User sees honest command surface. | Low. | no |

## First Fix To Implement

Start with P0 provider/state contracts in this order:

1. State reducers for `ui_events` and `tool_results`.
2. System context + tool binding in provider layer.
3. Tool-call AI message + ToolMessage result feedback.
4. Project root default fix.
5. Skill subgraph and allowed-tool enforcement.

That order gives immediate observability before changing provider/tool behavior.
