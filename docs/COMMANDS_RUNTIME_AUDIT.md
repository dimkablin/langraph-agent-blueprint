# Commands Runtime Audit

## Post-Fix Status (2026-05-06)

Required slash commands now execute through the graph command route and preserve command lifecycle events:

| Command | Post-fix status | Evidence |
| --- | --- | --- |
| `/help` | `working` | Lists enabled commands and separates unsupported optional commands. |
| `/clear` | `working` | Clears message history using `RemoveMessage(REMOVE_ALL_MESSAGES)`. |
| `/compact` | `working` | Routes directly to compaction path and emits `compact_finished`. |
| `/resume` | `working` | Loads named/latest session messages, todos, memory, usage, and metadata. |
| `/export` | `working` | Calls `ExportService`, creates a transcript file, updates `exported_outputs`. |
| `/skills` | `working` | Shows enabled skills plus disabled optional skills. |
| `/status` | `working` | Shows provider/model/session/project_root/cwd/storage/tool/skill/command counts. |
| `/cost` | `working` | Shows usage and honest `Cost: unavailable` when pricing is absent. |
| `/config` | `working` | Shows redacted effective config with separate `project_root` and `storage_dir`. |
| `/doctor` | `working` | Calls `DiagnosticsService`. |
| `/memory` | `working` | Loads durable memory from `MemoryService`; shows entries after remember. |
| `/todo` | `working` | Shows persisted todos in later turns. |

Optional commands remain explicitly unsupported/disabled and are separated in `/help`.

All commands are registered in `CommandRegistry` and parsed by `parse_slash_command`. The command router is reachable from CLI/API graph runs.

## Per-Command Findings

| Command | Expected behavior | Actual behavior | Parser/registry | Graph route | State update | Persistence | Test result | Status | Root cause | Fix needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/help` | Lists all registered commands; no LLM. | Lists all commands. | pass | local -> persist -> finalize | `final_response` | only final event survives | pass | `working` | command events overwritten | Add event reducer. |
| `/clear` | Clears conversation and persists clear. | Returns "Conversation cleared."; sets `clear_messages`. | pass | local | messages cleared in update | clear marker not durable | partial | `partially_working` | no session restore validation | Persist clear event/state. |
| `/compact` | Manual compaction creates summary and preserves recent context/todos. | Produces `Fake response: /compact`; metadata has compact route. | pass | not handled -> model -> compact | `compact_requested=True` | events lost | fail | `broken` | command is `handled=False`; compaction result not surfaced. | Route directly to compaction; respect manual flag. |
| `/resume` | Resume latest/specific session into usable graph state. | Returns "Resume requested..."; CLI subcommand can load session metadata/messages. | pass | local response | metadata `resume` | no graph state restore | partial | `partially_working` | command graph not connected to session restore. | Implement session lifecycle subgraph. |
| `/export` | Export transcript to file/structured output. | Returns "Export requested."; does not call `ExportService`. | pass | local response | metadata `export_requested` | no export file | fail | `registered_but_unreachable` | service not wired to command. | Execute export service in graph. |
| `/skills` | List loaded and disabled skills. | Lists loaded built-ins only. | pass | local response | final response | limited | pass/partial | `working` for loaded list | disabled skills hidden | Include disabled metadata. |
| `/status` | Provider/model/session/project_root/cwd/tool count/skill count. | Shows session id and model only. | pass | local response | final response | limited | partial | `partially_working` | handler too shallow | Expand status handler. |
| `/cost` | Usage/cost or unavailable. | Returns `Usage: {}` before model usage. | pass | local response | final response | no aggregate | partial | `partially_working` | usage not loaded/aggregated | Track session usage and unknown cost. |
| `/config` | Effective config with redacted secrets and clear paths. | Shows raw redacted dict. | pass | local response | final response | limited | partial | `partially_working` | default root can be `.storage`; formatting raw | Fix root and format. |
| `/doctor` | Run diagnostics. | Says diagnostics tool is available. | pass | local response | final response | no | fail | `registered_but_unreachable` | not connected to `DiagnosticsService`. | Wire command to service/tool. |
| `/memory` | Show durable user/project/session memory. | Shows scopes in current state; initially none. | pass | local response | final response | no | partial | `partially_working` | remember skill not writing memory through graph | Connect MemoryService and command. |
| `/todo` | Show visible todo list after `todo_write`. | Shows current state's `todos`; later invocation starts fresh. | pass | local response | final response | todos saved but not restored | partial | `partially_working` | session state not reconstructed between turns | Restore todos by session/thread. |
| `/prompt` | Expand args into model prompt. | Works with fake provider: `Fake response: sample args`. | pass | prompt -> model | adds `HumanMessage` | normal session | pass/partial | `partially_working` | real provider lacks system/tool context | Provider fixes. |
| `/skill` | Invoke skill runtime. | Renders skill prompt and calls model; no tool runtime under skill. | pass | skill_graph -> model | `active_skill`, `allowed_tools_override` | no skill record | partial | `partially_working` | skill graph is prompt expansion only | Implement skill subgraph. |
| `/rewind` | Rewind conversation. | Recognized but not implemented. | pass | local response | none | no | fail | `unsupported` | placeholder | Implement or hide. |
| `/branch` | Branch helper. | Recognized but not implemented. | pass | local response | none | no | fail | `unsupported` | placeholder | Implement or hide. |
| `/rename` | Rename session. | Recognized but not implemented. | pass | local response | none | no | fail | `unsupported` | placeholder | Implement or hide. |
| `/tag` | Tag session. | Recognized but not implemented. | pass | local response | none | no | fail | `unsupported` | placeholder | Implement or hide. |
| `/context` | Show context usage. | Recognized but not implemented. | pass | local response | none | no | fail | `unsupported` | placeholder | Implement or hide. |
| `/plugins` | List plugin state. | Recognized but not implemented. | pass | local response | none | no | fail | `unsupported` | placeholder | Implement or hide. |
| `/mcp` | List MCP state. | Recognized but not implemented. | pass | local response | none | no | fail | `unsupported` | placeholder | Implement or hide. |

## Cross-Cutting Command Issue

Every command audit result returned `ui_event_types: ["final_response"]` because earlier `command_started` / `command_finished` events are overwritten by later nodes. This is not a command-router failure; it is a state reducer/event persistence failure.
