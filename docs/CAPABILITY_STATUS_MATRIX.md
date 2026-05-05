# Capability Status Matrix

Status terms follow the user's requested vocabulary. `working` is used only where an end-to-end runtime path was proven, not merely where a class or test exists.

## Post-Fix Summary (2026-05-06)

P0/P1 runtime blockers from the audit have been fixed and covered by passing regression tests. Required slash commands are working end-to-end. Required tools are working end-to-end except network-dependent tools, which are now honestly disabled/unavailable by config/provider state. Built-in skills invoke the graph skill runtime, emit lifecycle events, enforce allowed-tool scope, and can continue through the shared model/tool loop; `remember` also writes durable memory.

Required capability status:

| Group | Status |
| --- | --- |
| Required slash commands | `working` |
| File/search/shell/notebook/todo tools | `working` |
| `web_fetch` | `disabled_by_config` unless network is enabled and approved |
| `web_search` | `disabled_by_config` / unavailable unless a provider is configured |
| Built-in skills | `working_with_documented_limits` |
| Optional commands | `unsupported/disabled` and separated in `/help` |
| P0/P1 blockers | `0 broken` |

Evidence:

- `python -m pytest` passes.
- Runtime smoke passed for fake provider commands/tools/skills/session/streaming.
- Ollama `qwen3:14b` successfully emitted a native `read_file` tool call through the graph and produced a final answer from the tool result.

## Original Audit Summary Counts

Approximate current capability classification:

| Group | Count |
| --- | ---: |
| Capabilities audited | 44 |
| `working` | 4 |
| `partially_working` | 20 |
| `broken` | 5 |
| `registered_but_unreachable` | 9 |
| `blocked_by_config` | 2 |
| `unsupported` / `disabled_by_design` | 4 |

The high number of partial statuses is caused by one common pattern: registry entries and direct execution exist, but the real model/provider and event/state contracts are incomplete.

## Matrix

| Capability | Type | Exists in code | Registered | Reachable from CLI/API | Reachable from model | Executes | Events visible | Persisted | Status | Evidence | Root cause | Required fix |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/help` | command | yes | yes | yes | n/a | yes | final only | limited | `working` | `/help` lists all registered commands. | Event history lost, but command works. | Add event reducer for command events. |
| `/clear` | command | yes | yes | yes | n/a | response only | final only | event limited | `partially_working` | Returns "Conversation cleared."; sets `clear_messages`. | No persisted clear marker beyond overwritten events. | Persist command lifecycle and verify messages clear in resumed state. |
| `/compact` | command | yes | yes | yes | n/a | partial | final only | limited | `broken` | Returns `Fake response: /compact`; metadata has `compact_requested`, `compact_route=compact`. | Manual compaction turns into model call; compact events/summary not visible. | Route manual compact directly to compaction and preserve events. |
| `/resume` | command | yes | yes | yes | n/a | response only | final only | no continuation | `partially_working` | Returns "Resume requested for session: latest". | Command does not load state into graph. | Implement session lifecycle graph route. |
| `/export` | command | yes | yes | yes | n/a | response only | final only | no export file | `registered_but_unreachable` | Returns "Export requested."; no export path. | Command sets metadata but never calls `ExportService`. | Route to export service/subgraph. |
| `/skills` | command | yes | yes | yes | n/a | yes | final only | limited | `working` | Lists eight loaded skills. | Disabled skills not shown separately. | Include disabled registry metadata. |
| `/status` | command | yes | yes | yes | n/a | partial | final only | limited | `partially_working` | Shows session/model only. | Missing project_root/cwd/tool count/skill count. | Expand status command. |
| `/cost` | command | yes | yes | yes | n/a | partial | final only | no | `partially_working` | Returns `Usage: {}` before any model usage. | No persisted/session aggregate cost fields. | Add usage aggregation and "cost unavailable" semantics. |
| `/config` | command | yes | yes | yes | n/a | partial | final only | limited | `partially_working` | Shows redacted config. | Default root may be `.storage`; output is raw dict. | Fix project root; format config clearly. |
| `/doctor` | command | yes | yes | yes | n/a | placeholder | final only | no | `registered_but_unreachable` | Says diagnostics tool is available. | Does not call `DiagnosticsService`. | Route command to diagnostics service. |
| `/memory` | command | yes | yes | yes | n/a | read only | final only | no | `partially_working` | Shows `Memory scopes: none`. | It reads current state, not durable service content after remember skill. | Connect memory graph/service to command and remember skill. |
| `/todo` | command | yes | yes | yes | n/a | read only | final only | limited | `partially_working` | Shows `Todos: []`. | New invocations reset state unless session restore implemented. | Persist and restore todos by session/thread. |
| Optional commands `/rewind`, `/branch`, `/rename`, `/tag`, `/context`, `/plugins`, `/mcp` | command | yes | yes | yes | n/a | no | final only | no | `unsupported` | Return "recognized but not implemented". | Placeholders. | Implement or mark disabled instead of active. |
| `batch` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no | `partially_working` | `/skill batch` renders prompt and allowed tools. | Skill runtime is prompt expansion only. | Implement skill subgraph and tool narrowing. |
| `debug` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no | `partially_working` | `/skill debug` renders prompt. | No tool loop under skill context. | Same as above. |
| `remember` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no memory write | `partially_working` | `/skill remember` renders prompt. | Does not call MemoryService or write memory. | Implement remember graph/tool path. |
| `simplify` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no | `partially_working` | `/skill simplify` renders prompt. | No side-effect gating or edit tool use. | Skill subgraph plus provider tool binding. |
| `skillify` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no file write | `partially_working` | `/skill skillify` renders prompt. | No write/edit execution path. | Same as above. |
| `stuck` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no | `partially_working` | `/skill stuck` renders prompt. | Prompt-only. | Same as above. |
| `update-config` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no config write | `partially_working` | `/skill update-config` renders prompt. | No config mutation workflow. | Config service + permissioned file updates. |
| `verify` | skill | yes | yes | via `/skill` | no real provider | prompt only | final only | no shell evidence | `partially_working` | `/skill verify` renders prompt; no command runs. | No bound tools and no skill tool loop. | Provider binding + shell permission path. |
| `read_file` | tool | yes | yes | fake graph | no Ollama | yes | final only | tool_call yes | `partially_working` | Fake graph reads file; outside root blocked. | Real model cannot call; events lost. | Provider binding, events reducer, ToolMessage. |
| `write_file` | tool | yes | yes | fake graph | no Ollama | with approval | final only | tool_call yes | `partially_working` | Special fake syntax approves and writes. | Generic fake JSON special-case misparses; real model cannot call. | Provider binding, robust fake parser, diff output. |
| `edit_file` | tool | yes | yes | fake graph | no Ollama | with approval and `allow_unread` | final only | tool_call yes | `partially_working` | No-prior-read correctly errors; `allow_unread` succeeds. | Prior-read history not durable across turns. | Persist read history and explicit approval semantics. |
| `notebook_read` | tool | yes | yes | fake graph | no Ollama | yes | final only | tool_call yes | `partially_working` | Reads sample `.ipynb`. | Real model cannot call; invalid-notebook handling not surfaced well. | Provider binding and errors/events. |
| `notebook_edit` | tool | yes | yes | fake graph likely | no Ollama | not fully audited | final only | likely | `unknown_needs_more_testing` | Class exists; tests do not cover E2E edit. | Requires approval and existing cell. | Add E2E fake-provider approval test. |
| `glob` | tool | yes | yes | fake graph | no Ollama | yes | final only | tool_call yes | `partially_working` | Finds `README.md`. | Real model cannot call; no output truncation in service. | Provider binding and event reducer. |
| `grep` | tool | yes | yes | fake graph | no Ollama | fails on Windows rg output | final only | tool_call error | `broken` | ValueError parsing `C:\...` path as line number. | Splits ripgrep output by `:` without Windows drive handling. | Use `rg --json` or robust parser. |
| `bash` | tool | yes | yes | fake graph | no Ollama | with approval | final only | tool_call yes | `partially_working` | Approve `echo audit-shell` returns `Tool bash ok`. | Real model cannot call; shell safety is coarse. | Provider binding and shell command classifier hardening. |
| `powershell` | tool | yes | yes | fake graph likely | no Ollama | not fully audited | final only | likely | `unknown_needs_more_testing` | Registered on Windows. | Needs E2E approval test. | Add platform-aware test and provider binding. |
| `web_fetch` | tool | yes | yes | fake graph | no Ollama | disabled by config | final only | tool_call error | `blocked_by_config` | `NETWORK_ENABLED=false` gives PermissionError. | Expected default; real model cannot call. | Keep disabled-by-config status; add provider config. |
| `web_search` | tool | yes | yes | fake graph | no Ollama | empty provider | final only | tool_call yes | `blocked_by_config` | With network enabled returns 0 results. | No search provider configured. | Add provider abstraction or mark unavailable in context. |
| `todo_write` | tool | yes | yes | fake graph | no Ollama | yes | final only | todos saved in session | `partially_working` | Updates todos in same graph result. | `/todo` in later invocation does not restore state. | Persist/restore session state. |
| `agent` | tool | yes | yes | fake graph | no Ollama | synthetic result | final only | tool_call yes | `partially_working` | Service returns "Subagent completed". | No actual child graph/model run. | Implement child graph runtime. |
| `skill` | tool | yes | yes | fake graph | no Ollama | prompt expansion | final only | no invocation record | `partially_working` | Fake `tool:skill` routes to skill prompt. | Real model cannot call; not a full skill subgraph. | Provider binding and skill events/persistence. |
| `diagnostics` | tool | yes | yes | fake graph possible | no Ollama | direct service | final only | tool_call if invoked | `registered_but_unreachable` | `/doctor` does not call it. | Command not routed to tool/service. | Wire `/doctor` to diagnostics. |
| MCP adapters | tool/service | minimal | mock only | no real config | no | mock only | no | no | `disabled_by_design` | Tests register mocked MCP tool only. | No server lifecycle/invocation runtime. | Implement MCP client or keep disabled. |
| Plugins | service | minimal | manifests only | not commands/tools | no | no | no | no | `registered_but_unreachable` | PluginService discovers manifests, registries do not consume them. | Contributions not wired into registries. | Integrate plugin contributions. |
