# Source Traceability Recheck

Current audit date: 2026-05-07

Reference source:

```text
C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project
```

Current project:

```text
C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint
```

Status vocabulary:

- `working`: current runtime has a direct working equivalent.
- `working_with_different_architecture`: current runtime works, but via LangGraph/Pydantic/plugin redesign.
- `partial`: meaningful subset exists, but source behavior is broader.
- `missing`: source capability is not implemented in current runtime.
- `intentionally_skipped`: consciously not ported for MVP or safety.
- `future_frontend`: belongs to future UI/frontend work.
- `future_non_mvp`: outside MVP.
- `extension_not_source`: current capability is an added architecture extension.
- `needs_review`: requires deeper source-specific review before prioritizing.

## Status Counts

Rechecked capability lines: 74

| Status | Count |
| --- | ---: |
| working | 7 |
| working_with_different_architecture | 17 |
| partial | 19 |
| missing | 6 |
| intentionally_skipped | 4 |
| future_frontend | 5 |
| future_non_mvp | 7 |
| extension_not_source | 8 |
| needs_review | 1 |

## Matrix

| Source capability | Source location | Current equivalent | Current status | Port type | Missing pieces | Priority | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Interactive terminal chat | `src/entrypoints/cli.tsx`, `src/components` | `lg-agent chat`, `AssistantGraphRuntime.invoke` | working_with_different_architecture | redesigned_as_langgraph | Rich TUI remains future. | P1 | CLI reuses session id across turns. |
| Headless query | `src/query`, `src/cli/structuredIO.ts` | `lg-agent query` | working_with_different_architecture | redesigned_as_langgraph | Some SDK event variants absent. | P2 | Basic text/json/stream-json exists. |
| Stream JSON / NDJSON | `src/cli/ndjsonSafeStringify.ts`, structured IO | `runtime.stream`, `--output stream-json` | working_with_different_architecture | redesigned_as_langgraph | Source has broader SDK event taxonomy. | P2 | Tests cover stream-json events. |
| SDK/API schemas | `src/entrypoints/sdk`, `src/schemas`, `src/server` | FastAPI routes and API schemas | partial | redesigned_as_langgraph | Complete SDK contract and native host direct-connect are absent. | P2 | Frontend contract tests exist. |
| Native/direct-connect/remote host modes | `src/server`, `src/remote`, `src/bridge`, `src/native-ts` | None | future_non_mvp | not_ported | Native host, remote session, teleport, desktop/mobile. | not_mvp | Do not pull into MVP. |
| Core agent query loop | `src/query`, `src/services/tools/toolOrchestration.ts` | Main StateGraph | working_with_different_architecture | redesigned_as_langgraph | Source-specific retry details not all ported. | P1 | Graph edges now own flow. |
| Checkpoint and interrupt/resume | Source permission/UI state | LangGraph checkpointer plus permission interrupt/resume | working_with_different_architecture | redesigned_as_langgraph | UI picker remains future. | P1 | Stronger graph-owned behavior. |
| Concurrent tool batches | Source tool orchestration and model tool-use loop | Sequential graph route over pending tool calls | partial | redesigned_as_langgraph | Multiple parallel tool calls in one assistant message. | P1 | Important for subagents/performance later. |
| Provider advanced behavior | `src/services/api/claude.ts`, model utilities | Provider abstraction | partial | redesigned_as_langgraph | Prompt caching, thinking, betas, richer retries/cost. | P2 | OpenAI/Ollama/fake paths exist. |
| Token budget/context accounting | `src/query/tokenBudget.ts`, `src/utils/tokens.ts` | Compaction thresholds and usage service | partial | redesigned_as_langgraph | Full context-window accounting and visualization. | P1 | Ties into Phase 6. |
| Read tool | `src/tools/FileReadTool` | `read_file` | working | direct_port | Rich display only. | P2 | Permission/read tracking covered. |
| Write tool | `src/tools/FileWriteTool` | `write_file` | working | direct_port | Rich diff UI. | P2 | Permission approval covered. |
| Edit tool | `src/tools/FileEditTool` | `edit_file` | working_with_different_architecture | redesigned_as_langgraph | Source has richer patch/diff matching. | P2 | Current exact-once guard is safer. |
| MultiEdit / patch batch | `src/tools/FileEditTool/utils.ts` list-edit support | None | missing | not_ported | Multi-edit transactional behavior. | P1 | Useful before large coding workflows. |
| Notebook tools | `src/tools/NotebookReadTool`, `NotebookEditTool` | `notebook_read`, `notebook_edit` | working | direct_port | UI rendering differences. | P2 | Runtime tests cover edit approval. |
| Glob/Grep tools | `src/tools/GlobTool`, `GrepTool` | `glob`, `grep` | working | direct_port | Source ranking/UI polish. | P3 | Core search works. |
| Bash/PowerShell tools | `src/tools/BashTool`, `PowerShellTool` | `bash`, `powershell` | working_with_different_architecture | redesigned_as_langgraph | Source has more command parsing and shell UX. | P1 | Permissions are metadata-driven. |
| WebFetch/WebSearch | `src/tools/WebFetchTool`, `WebSearchTool` | `web_fetch`, `web_search` | partial | redesigned_as_langgraph | Search provider integration. | P2 | Fetch has stronger guardrails; search disabled without provider. |
| TodoWrite | `src/tools/TodoWriteTool` | `todo_write` | working | direct_port | Source task integration broader. | P2 | Persisted todo coverage exists. |
| Ask user question tool | `src/tools/AskUserQuestionTool` | Permission interrupts only | missing | not_ported | Model-callable user elicitation. | P2 | Could use hook/permission primitives later. |
| Enter/exit plan mode tools | `src/tools/EnterPlanModeTool`, `ExitPlanModeTool` | Permission mode plus docs | partial | redesigned_as_langgraph | Tool-callable plan mode and approval UI. | P2 | Current `plan` permission mode exists. |
| Worktree tools | `src/tools/EnterWorktreeTool`, `ExitWorktreeTool` | None | missing | not_ported | Worktree lifecycle and path safety. | P2 | Can wait until real subagents. |
| LSP/IDE tools | `src/tools/LSPTool`, IDE commands | None | future_non_mvp | not_ported | LSP server/client and IDE bridge. | not_mvp | Explicitly out of MVP. |
| ToolSearch / deferred tools | `src/tools/ToolSearchTool`, `src/utils/toolSearch.ts` | Tool list and registry snapshot | missing | not_ported | Model-callable deferred tool discovery. | P2 | Useful for large tool/plugin surfaces. |
| Agent/subagent tool | `src/tools/AgentTool`, `src/coordinator`, `src/tasks` | `agent`, `agent_graph`, `SubagentRequest`, child-run storage | working_with_different_architecture | redesigned_as_langgraph | Nested approval resume, parallel/background teams, stop/list/show task lifecycle. | P1 | Phase 5 real local child graph implemented; broader task/team lifecycle remains future. |
| Background task/team tools | `src/tools/Task*`, `Team*`, `SendMessageTool`, remote tasks | Limited `task` placeholder, not core registered | future_non_mvp | not_ported | Teams, remote polling, background tasks. | not_mvp | Real subagents first. |
| Built-in core skills | `src/skills/bundled` | built-in SKILL.md definitions | working_with_different_architecture | redesigned_as_skill | Some source optional skills disabled. | P2 | Typed args and SkillEffect added. |
| Optional bundled skills | `loop`, `scheduleRemoteAgents`, `keybindings`, `claudeApi`, etc. | Disabled/optional docs | intentionally_skipped | not_ported | Only needed if product goals require. | not_mvp | Avoid source-specific or UI-specific skills in MVP. |
| SkillTool | `src/tools/SkillTool` | `skill` tool and `skill_graph` | working_with_different_architecture | redesigned_as_skill | Source inline/fork behavior differs. | P1 | Plugin skills work. |
| Project/user file skills | `src/skills/loadSkillsDir.ts` | `SkillLoader`, config `skills_paths` | working | redesigned_as_skill | Advanced source gates. | P2 | Local file loading covered. |
| Skill frontmatter advanced fields | Source skill metadata and command types | allowed_tools and typed args | partial | redesigned_as_skill | model/effort/hooks/context/path/shell/gates. | P2 | Add only after config/SDK hardening. |
| MCP prompts as skills | MCP prompt builders | MCP prompts discover/get | partial | redesigned_as_mcp | Default prompt-to-skill registration. | P2 | Documented limitation. |
| Core slash commands | `src/commands` core subset | `/help`, `/clear`, `/compact`, `/resume`, `/export`, `/skills`, etc. | working | redesigned_as_langgraph | Rich local JSX UI absent. | P2 | Command tests exist. |
| Optional session commands | `/rewind`, `/branch`, `/rename`, `/tag`, `/context` | Recognized placeholders | partial | not_ported | Real operations and tests. | P2 | Current docs honestly mark unsupported. |
| Auth/model/update commands | `/login`, `/logout`, `/model`, `/upgrade`, `/config` | `/config`, env config, provider selection | partial | redesigned_as_langgraph | Interactive auth/model/update flows. | P2 | Phase 8. |
| TUI commands and modes | theme, keybindings, voice, vim, mobile, desktop | None or docs only | future_frontend | not_ported | UI state and input systems. | frontend_phase | Not runtime MVP. |
| Plugin/MCP/hooks commands | `/plugin`, `/mcp`, `/hooks` | `/plugins`, `/mcp`, `/hooks`; CLI plugin commands | working_with_different_architecture | redesigned_as_plugin | Source has richer menus/auth. | P2 | Current commands are diagnostic and graph-facing. |
| Hook lifecycle | `src/types/hooks.ts`, `src/utils/hooks.ts` | typed graph-owned hooks | working_with_different_architecture | redesigned_as_hook | Source has more hook events. | P1 | Safer controlled HookResult. |
| Executable hooks | Source hook callbacks/scripts | Data-only declarative hooks | intentionally_skipped | redesigned_as_hook | Trust policy for executable hooks. | not_mvp | Correct safety choice for MVP. |
| MCP stdio tools/resources/prompts | `src/services/mcp`, MCP tools | MCP stdio client runtime | working_with_different_architecture | redesigned_as_mcp | HTTP/OAuth and richer resource storage. | P1 | Fake stdio server tests exist. |
| MCP HTTP/OAuth/auth | MCP auth services and `McpAuthTool` | HTTP config placeholder only | future_non_mvp | not_ported | OAuth, registry, connectors. | not_mvp | Can be Phase 8+ if needed. |
| MCP server mode | Source `entrypoints/mcp.ts` | None | future_non_mvp | not_ported | Server mode. | not_mvp | Explicitly not in current phases. |
| Plugin install/skills/hooks/policies | `src/plugins`, `src/services/plugins` | `PluginService`, Superpowers, hooks, policies | working_with_different_architecture | redesigned_as_plugin | Marketplace/bundled plugin polish. | P1 | Batch 2 cleaned policy extension. |
| Plugin command/tool/MCP SDK | Source plugin contribution types | Skills/hooks/policies; commands/MCP partial | partial | redesigned_as_plugin | Commands, tools, MCP contributions as first-class SDK. | P1 | Phase 8. |
| Superpowers plugin | Not source | external plugin integration | extension_not_source | extension | N/A | P1 | Keep classified as extension. |
| Memory remember scopes | `src/memdir`, `remember.ts` | `MemoryService`, `/memory`, `SkillEffect` | working_with_different_architecture | redesigned_as_skill | Source memory relevance richer. | P1 | Durable side effect now controlled. |
| Memory extraction/relevance/team memory | `src/services/extractMemories`, `SessionMemory`, `teamMem*` | Basic memory context | partial | redesigned_as_langgraph | Automatic extraction and relevance search. | P2 | Could follow attachments/context. |
| Sessions resume/export/persist | source session storage and commands | `SessionStorage`, `/resume`, `/export` | working_with_different_architecture | redesigned_as_langgraph | UI picker and richer metadata. | P2 | Runtime ID hardening is stronger. |
| Session browser/rename/tag/rewind/branch | source commands/screens | Placeholders for some commands | partial | not_ported | Real operations and frontend UX. | P2 | Keep after eval/replay. |
| Compaction | `src/services/compact` | compaction graph/service | working_with_different_architecture | redesigned_as_langgraph | Source prompt variants and cleanup logic. | P1 | Hooks around compaction exist. |
| Microcompact/session-memory compaction | `apiMicrocompact`, `microCompact`, `sessionMemoryCompact` | Threshold-based compact | partial | redesigned_as_langgraph | Fine-grained compaction modes. | P2 | Phase 6/7 after replay. |
| Context providers and attachments | `src/utils/attachments.ts`, context components | Mostly missing | missing | not_ported | At-mentions, images, PDFs, pasted content, git/IDE context. | P1 | Phase 6. |
| Context visualization | `src/components/ContextVisualization.tsx` | No runtime/frontend equivalent | future_frontend | not_ported | UI and token breakdown. | frontend_phase | Depends on Phase 6. |
| Usage/cost | `/cost`, usage utilities, telemetry | `/cost`, `UsageService` | partial | redesigned_as_langgraph | Provider-specific cost accounting. | P2 | Could be before frontend. |
| Telemetry/analytics | source analytics/telemetry | Langfuse extension only | intentionally_skipped | not_ported | Source analytics products. | not_mvp | Do not port telemetry wholesale. |
| Langfuse observability | Not source | `ObservabilityService` | extension_not_source | extension | Live-key smoke remains manual. | P1 | Current no-op disabled mode. |
| Pydantic boundary models | Not source | models package | extension_not_source | extension | Continue tightening boundaries. | P1 | Major architecture improvement. |
| Metadata-driven tool semantics | Not source | `ToolPermissionMetadata`, `ToolRuntimeMetadata` | extension_not_source | extension | Broader plugin SDK docs. | P1 | Avoids name semantics. |
| Strict runtime IDs | Not source | `utils.ids`, storage/API validation | extension_not_source | extension | N/A | P0 closed | Batch 1. |
| Immutable ToolExecutionContext | Not source | minimal context DTO | extension_not_source | extension | N/A | P1 closed | Batch 1. |
| Edit/web_fetch hardening | Source has different behavior | exact-once edit and web guardrails | extension_not_source | extension | N/A | P1 closed | Batch 1. |
| Generic plugin policy and SkillEffect | Not source | plugin policies and skill effects | extension_not_source | extension | More policy types later. | P1 closed | Batch 2. |
| Frontend API shell | Source React+Ink TUI | React frontend static shell plus API contract | partial | ui_replacement | Real frontend UX. | frontend_phase | Runtime readiness first. |
| Full TUI permission/resume/tool UI | `src/components`, `src/screens`, `src/ink` | CLI text output | future_frontend | not_ported | Dialogs, picker, diff rendering, shortcuts. | frontend_phase | Later. |
| Config layering/settings | source settings/config services | env plus `.env` precedence | partial | redesigned_as_langgraph | Project/user config layering and command edits. | P1 | Phase 8. |
| Provider auth/feature gates | source auth/model/feature systems | env keys and provider abstraction | partial | redesigned_as_langgraph | Login/logout/model command flows and feature gates. | P2 | Phase 8. |
| Eval/replay harness | Not a clear source first-class feature | None | missing | extension_needed | Replay transcript and acceptance scenarios. | P1 | Phase 7. |
| Data analyst artifacts/datasets | Not source | None | intentionally_skipped | not_ported | N/A | not_mvp | Not part of source runtime. |
| Release/update flow | source update/upgrade commands | None | future_non_mvp | not_ported | Distribution updater. | not_mvp | Keep out of reference MVP. |
| Remote bridge/teleport/desktop/mobile | `src/remote`, `src/bridge`, commands | None | future_non_mvp | not_ported | Remote session infra. | not_mvp | Out of current product scope. |
| Voice input | `src/voice`, `useVoice` | None | future_frontend | not_ported | STT/input UX. | frontend_phase | Not runtime blocker. |
| Keybindings/vim mode | `src/keybindings`, `src/vim` | None | future_frontend | not_ported | Terminal input layer. | frontend_phase | Optional only. |
| Regression test harness | Source unknown/mixed | 73 current test files plus runtime audit tests | working_with_different_architecture | extension | Dedicated replay/eval absent. | P1 | Strong tests, but Phase 7 still needed. |
| Plugin marketplace exact compatibility | source plugin marketplace/services | local/git plugin service | needs_review | redesigned_as_plugin | Manifest compatibility and marketplace rules. | P2 | Review before public plugin SDK. |
