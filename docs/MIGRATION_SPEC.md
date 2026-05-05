# Migration Spec

## Basis

This migration spec is based on:

- `docs/SOURCE_AUDIT.md`
- `docs/SKILLS_AUDIT.md`
- `docs/FEATURE_TRACEABILITY_MATRIX.md`

No Python/LangGraph production code has been created in this audit phase.

## Source Facts That Drive The Migration

- Requested source path `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-like-project` was not present.
- The audited source path is `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project`.
- A second same-sized candidate source tree exists at `C:\Users\dimka\Documents\PROJECTS\claude-code-like-project`.
- `package.json` was not present in either inspected source tree. Dependency and entrypoint information must therefore be inferred from source imports, `README.md`, and runtime scripts.
- The audited project is a TypeScript/Bun React+Ink terminal assistant, not a conventional browser React data analyst application.
- The source contains explicit skill infrastructure and many tool/capability implementations.
- The source does not contain a first-class data analyst workflow for CSV/Excel/Parquet dataframe profiling, chart artifact generation, artifact editing, or browser artifact preview.
- Because the README describes the code as reconstructed/leaked Claude Code source, the migration should preserve product behavior and capability boundaries, but should not copy proprietary prompts or implementation text verbatim.

## What Is Being Ported

| Source capability | Porting decision |
| --- | --- |
| Interactive chat/REPL loop | Port to LangGraph conversational graph with a terminal or API UI adapter. |
| Headless `query()` / SDK-style execution | Port to a Python service entrypoint that invokes the same graph without TUI state. |
| Model streaming and assistant turns | Port to a LangGraph model node and streaming event adapter. |
| Tool registry and tool execution | Port to Python tool registry, tool schemas, permission checks, and LangGraph tool execution nodes. |
| File read/write/edit/notebook tools | Port as Python tools/services with sandbox and confirmation enforcement. |
| Search tools (`Glob`, `Grep`) | Port as Python filesystem search services. |
| Shell/Bash tool | Port as a Python shell tool behind explicit permissions and platform-specific safety checks. |
| Web fetch/search tools | Port as web service tools if network policy allows them in the deployed environment. |
| MCP tools and resources | Port as MCP client/registry service plus LangGraph nodes for discovery and invocation. |
| Slash commands | Port as command registry and command-router node. |
| Skill loading and SkillTool | Port as skill registry, skill invocation node/subgraph, and prompt-template layer. |
| Bundled skills | Port as built-in skill definitions with equivalent names and behavior. |
| Permissions and user confirmations | Port as human-in-the-loop LangGraph interrupt/pending-confirmation state. |
| Plan mode | Port as a planning subgraph with a no-write policy until approval. |
| Todo/task management | Port as task-state service and graph nodes that update task state. |
| Subagents | Port as subgraph/child-run execution with isolated state and optional context forking. |
| Session persistence/resume | Port as storage layer with message, tool-call, and context snapshots. |
| Clear, rewind, compact | Port as session-state transformations and compaction graph nodes. |
| Context visibility | Port as context accounting service and API/UI telemetry. |
| Memory/remember | Port as memory extraction and memory storage services. |
| Hooks | Port as hook dispatcher called around graph/tool/skill lifecycle events. |
| Plugins | Port as plugin discovery service that can contribute commands, skills, hooks, and tools. |
| Export transcript | Port as export service over persisted conversation state. |
| Insights/report generation | Port as report service over session logs and runtime metadata. |
| Settings/config/model selection | Port as configuration service and provider registry. |
| Cost/status indicators | Port as usage telemetry service exposed to UI/API. |
| IDE/LSP diagnostics | Port as optional integration service, not required for first core graph. |
| Keybindings/voice/paste UI behavior | Port only if a terminal UI is retained; otherwise replace with API/browser UI behavior. |

## What Is Not A Direct Source Feature

The following requested data analyst features were not found as first-class source behavior in the audited project:

- CSV/Excel/JSON/Parquet dataset ingestion
- dataframe profiling
- dataset question answering
- analysis planning specific to tabular data
- safe execution of generated Python analysis code against datasets
- chart artifact creation
- artifact preview/edit/download for analysis outputs
- browser React data analyst screens

These can still be implemented in the new Python/LangGraph project, but they would be new product capabilities rather than a direct functional port of the audited source. If included, they should be specified as extensions and traced separately from source-preservation work.

## LangGraph Architecture

### Graph State

The primary LangGraph state should be a Pydantic model or typed dictionary containing:

| State field | Purpose |
| --- | --- |
| `session_id` | Stable session identifier. |
| `project_root` | Active working directory/project root. |
| `messages` | Conversation messages and model/tool events. |
| `input_text` | Latest normalized user input. |
| `attachments` | Files/images pasted or attached by the user. |
| `active_command` | Parsed slash command, if any. |
| `active_skill` | Skill requested directly or selected by the model. |
| `available_tools` | Tool registry after config, permissions, MCP, plugins, and skills are applied. |
| `pending_tool_calls` | Tool calls proposed by the model. |
| `tool_results` | Results returned by tool execution nodes. |
| `permissions` | Runtime permission policy and decisions. |
| `pending_confirmation` | Human approval request waiting for a user response. |
| `todos` | Current todo/task plan. |
| `memory` | Loaded user/project memory. |
| `context_status` | Token/context accounting and compaction thresholds. |
| `usage` | Model cost/token telemetry. |
| `errors` | Recoverable and terminal errors. |
| `ui_events` | Streaming events for terminal/API/browser clients. |
| `artifacts` | Output references for transcripts, reports, files, and optional future data-analysis artifacts. |

### Core Nodes

| LangGraph node | Source basis | Responsibility |
| --- | --- | --- |
| `bootstrap_config` | `src/utils/config.ts`, `src/utils/flags.ts`, `src/utils/state.ts` | Load config, CLI flags, defaults, and provider settings. |
| `load_registries` | `src/tools.ts`, `src/commands.tsx`, `src/skills/loadSkillsDir.ts` | Load tools, commands, MCP tools, skills, hooks, and plugins. |
| `normalize_input` | `src/screens/REPL.tsx`, paste/upload hooks | Normalize text input, pasted content, and file attachments. |
| `command_router` | `src/commands.tsx`, `src/screens/REPL.tsx` | Route slash commands before model invocation. |
| `skill_router` | `src/tools/SkillTool/SkillTool.ts`, `src/skills/*` | Invoke explicit or model-selected skills. |
| `context_builder` | `src/context.ts`, `src/services/context.ts`, prompt files | Build system context, memory, project info, and tool prompt context. |
| `model_call` | `src/query.ts`, `src/services/claude.ts`, model services | Call the model and stream assistant events. |
| `tool_router` | `src/QueryEngine.ts`, `src/services/tools/toolOrchestration.ts` | Decide whether proposed tools need permission, execution, or deferral. |
| `permission_gate` | `src/permissions.ts`, permission UI/hooks | Request/validate user approval before side effects. |
| `tool_executor` | `src/services/tools/toolExecution.ts`, `src/tools/*` | Execute tools and capture structured results. |
| `hook_runner` | `src/hooks/hooks.ts`, `src/hooks/index.ts` | Run configured lifecycle hooks. |
| `compact_decision` | `src/utils/autoCompact.ts`, `src/utils/compact.ts` | Decide when context compaction is needed. |
| `compact_context` | compaction utilities and commands | Summarize/transform older state while preserving active work. |
| `persist_session` | `src/utils/log.ts`, `src/utils/conversationRecovery.ts` | Persist state, messages, tool calls, and recovery metadata. |
| `finalize_response` | `src/screens/REPL.tsx`, streaming utilities | Emit final client-visible response and status events. |
| `error_recovery` | `src/utils/errors.ts`, recovery utilities | Convert exceptions into recoverable graph state or final errors. |

### Subgraphs

| Subgraph | Purpose |
| --- | --- |
| Tool execution subgraph | Permission check, execution, result formatting, hooks, and persistence for each tool call. |
| Skill execution subgraph | Skill discovery, prompt-template assembly, allowed tool narrowing, optional forked context, and result merge. |
| Command subgraph | Built-in slash commands, custom commands, legacy `.claude/commands`, and command-specific UI/API output. |
| Agent/subagent subgraph | Child run creation, context forking, progress streaming, and result integration. |
| MCP subgraph | MCP server discovery, resource listing, schema conversion, and tool invocation. |
| Session lifecycle subgraph | resume, clear, rewind, compact, export, and transcript/report generation. |
| Plan/todo subgraph | planning state, task updates, user approval checkpoints, and no-write enforcement during planning. |

## Skills

The source has explicit skill infrastructure. The Python port should preserve:

- skill directory convention: `skill-name/SKILL.md`
- frontmatter-like metadata: name, description, allowed tools, model, effort, hooks, context behavior, agent behavior, paths, shell behavior
- dynamic/conditional skill loading
- legacy command compatibility where needed
- `SkillTool` as a model-invokable capability
- bundled skill names where behavior is still relevant

### Built-In Skill Mapping

| Source skill | Python/LangGraph target |
| --- | --- |
| `batch` | Skill template plus subagent/task subgraph helper for multi-step parallel work. |
| `claude-api` | Skill template for API guidance; should be rewritten generically or scoped to allowed model-provider docs. |
| `claude-api-content` | Skill template for provider content/API guidance. |
| `claude-in-chrome` | Optional browser-control integration skill if the target includes a browser UI/control service. |
| `debug` | Debugging workflow skill and error-recovery prompt template. |
| `keybindings-help` | UI help skill only if terminal UI keybindings are retained. |
| `loop` | Iterative execution skill/subgraph pattern. |
| `lorem-ipsum` | Non-critical utility skill; port only if compatibility is required. |
| `remember` | Memory write/extraction skill backed by memory service. |
| `schedule` | Automation/reminder skill only if the target runtime supports automations. |
| `simplify` | Prompt-driven rewrite/refactor skill. |
| `skillify` | Skill-creation skill for adding new skill definitions. |
| `stuck` | Recovery/debugging skill. |
| `update-config` | Config mutation skill behind permission confirmation. |
| `verify` | Verification workflow skill for test/build/check execution. |

### New Data Analyst Skills

Because data analyst behavior was requested but not found in the audited source, these should be treated as optional extension skills rather than source-port skills:

| Extension skill | Required services/tools |
| --- | --- |
| `load_dataset` | file ingestion service for CSV/Excel/JSON/Parquet |
| `profile_dataset` | dataframe profiling service |
| `answer_dataset_question` | analysis graph node plus dataframe context service |
| `plan_analysis` | planning prompt template and LangGraph plan node |
| `generate_python_analysis_code` | code-generation prompt and approval boundary |
| `execute_python_analysis_code` | sandboxed Python execution service |
| `create_visualization` | plotting/chart service |
| `create_analysis_artifact` | artifact storage/rendering service |
| `export_analysis_artifact` | export/download service |

These extension skills require separate acceptance criteria because they are not source-backed.

## Python Services And Tools

| Service/tool | Source basis | Responsibility |
| --- | --- | --- |
| `ModelProviderService` | model provider utilities | Provider selection, streaming, token usage, retries. |
| `ToolRegistry` | `src/tools.ts`, `src/Tool.ts` | Register tool schemas and implementations. |
| `ToolExecutionService` | `src/services/tools/*` | Validate, execute, log, and format tool results. |
| `PermissionService` | `src/permissions.ts`, permission UI | Side-effect classification and human approval. |
| `FileService` | `src/tools/Read`, `Write`, `Edit`, notebook tools | Safe filesystem operations. |
| `SearchService` | `src/tools/Glob`, `src/tools/Grep` | Fast project search. |
| `ShellService` | `src/tools/Bash*` | Shell command execution with policy checks. |
| `WebService` | `src/tools/WebFetch`, `src/tools/WebSearch` | Network fetch/search abstractions. |
| `MCPService` | `src/services/mcp*`, `src/utils/mcp*` | MCP client lifecycle and remote tool/resource handling. |
| `PluginService` | `src/plugins.ts`, marketplace utilities | Plugin discovery and contributions. |
| `SkillRegistry` | `src/skills/loadSkillsDir.ts` | Load and validate skills. |
| `CommandRegistry` | `src/commands.tsx`, command files | Built-in/custom command execution. |
| `SessionStorage` | logs/recovery utilities | Conversation persistence, resume, rewind, export. |
| `ConfigService` | config/state utilities | Settings, env, provider config, project config. |
| `MemoryService` | memory/remember utilities | User/project memory loading and updates. |
| `CompactionService` | compact/auto-compact utilities | Context summarization and pruning. |
| `TaskService` | todo/task tools | Todo state and task progress. |
| `AgentService` | Agent/Task tools | Child graph runs and result merge. |
| `HookService` | hook utilities | Lifecycle hook execution. |
| `UsageService` | cost/status utilities | Token, model, and cost telemetry. |
| `ExportService` | export command | Transcript/report export. |
| `ArtifactService` | not source-backed except exported/logged outputs | Optional future artifact preview/edit/download for data analyst extension. |

## Storage Layer

The storage layer should preserve source behavior around sessions and recovery:

| Stored object | Format recommendation | Notes |
| --- | --- | --- |
| Session metadata | JSON | session id, project root, model, timestamps, config snapshot. |
| Conversation events | JSONL | user/assistant/tool events, streaming can be reconstructed from final events if needed. |
| Tool call records | JSONL or embedded events | include inputs, outputs, approval decisions, errors, and duration. |
| Task/todo state | JSON | current and historical todo snapshots. |
| Memory | Markdown or JSON | preserve human-readable project/user memory where applicable. |
| Skill registry cache | JSON | resolved skill metadata and path provenance. |
| Plugin registry cache | JSON | installed plugin manifests and contributed capabilities. |
| Exported transcripts/reports | Markdown/HTML/JSON | source has transcript/report-like outputs, not general analysis artifacts. |
| Optional analysis artifacts | files plus JSON metadata | only for the data analyst extension, not a source port requirement. |

## API And UI Layer

The audited source UI is React+Ink terminal UI. A Python port can expose the graph through:

| Layer | Migration role |
| --- | --- |
| CLI/TUI | Closest functional replacement for the audited source. Use a terminal UI adapter over graph streaming events. |
| FastAPI/WebSocket API | Recommended if the target product must become a browser data analyst app. It should call the same LangGraph backend. |
| Browser React UI | UI replacement, not a direct port of source components. Should consume graph events and persisted artifacts. |
| Headless API/SDK | Direct replacement for source `query()` / `sdk.ts` behavior. |

If the product goal remains "Claude-like data analyst app", the browser UI and data-analysis services must be treated as an explicit redesign layer on top of the ported graph core.

## Prompts To Recreate

The port should recreate prompt categories, not copy prompt text verbatim:

| Prompt category | Source location examples | Python target |
| --- | --- | --- |
| Main system/context prompts | `src/constants/prompts.ts`, `src/context.ts`, model/context services | Prompt templates feeding `context_builder` and `model_call`. |
| Tool prompts | `src/tools/*/prompt.ts` | Tool-specific prompt metadata and schema descriptions. |
| Skill invocation prompt | `src/tools/SkillTool/prompt.ts` | SkillTool prompt template. |
| Built-in skill prompts | `src/skills/bundled/*/SKILL.md` | Built-in Python skill definitions. |
| Compact/summary prompts | compaction utilities/commands | Compaction prompt templates. |
| Memory prompts | memory extraction utilities and `remember` skill | Memory extraction/write templates. |
| Agent/task prompts | `Task`/Agent tool files and task services | Subagent/subgraph instruction templates. |
| Command prompts | command files and legacy command loader | Command-to-prompt adapters. |

## Artifacts

The source supports persisted conversation logs, exported transcripts/reports, and tool-created files. It does not expose a first-class artifact system for browser previews or data-analysis outputs.

Ported artifact behavior:

- user-created and tool-created files
- notebook/file edits
- conversation transcript export
- insights/report export
- structured tool outputs stored with session history

Optional extension artifact behavior:

- analysis result objects
- chart image/HTML outputs
- dataframe previews
- editable analysis reports
- download bundles

The optional extension needs explicit storage schema and UI behavior because it is not source-backed.

## Preserved User Scenarios

| Scenario | Preservation plan |
| --- | --- |
| Start interactive assistant in a project | CLI/TUI or browser client opens a LangGraph session with project context. |
| Ask a coding/project question | Model node answers with file/context tools available. |
| Ask the assistant to read or search files | File/search tools execute through permission-aware tool subgraph. |
| Ask the assistant to edit files | Write/edit tools require policy checks and persist session history. |
| Run shell commands | Shell tool requests approval according to permission policy. |
| Use slash commands | Command router executes built-in/custom commands. |
| Invoke a skill | Skill registry resolves skill and skill subgraph executes it. |
| Use MCP tools/resources | MCP service contributes tools/resources to available registry. |
| Resume a session | Storage layer reconstructs graph state and context. |
| Compact long context | Compaction node summarizes state and preserves active work. |
| Create/update todo plan | Task service and todo nodes update visible task state. |
| Delegate to a subagent | Agent service runs child graph and merges result. |
| Export conversation/report | Export service renders persisted events. |
| Recover from tool/model error | Error recovery node emits actionable state and allows retry. |

## Assumptions

| Assumption | Reason |
| --- | --- |
| `llm-data-analyst\claude-code-like-project` is the intended source tree. | Requested `claude-like-project` path was absent; this was the closest matching tree under the requested parent. |
| Missing `package.json` means dependency metadata is incomplete. | No `package.json` was found by exact or recursive search in inspected source trees. |
| The Python target should preserve behavior, not source implementation text. | Source provenance is unclear and README describes reconstructed/leaked source. |
| LangGraph is the orchestration core. | User explicitly requested Python and LangGraph rewrite. |
| Browser data analyst UI, if required, is a replacement layer. | Audited UI is terminal React+Ink, not browser React. |
| Data analyst capabilities are extension requirements unless another source tree exists. | No first-class analyst/dataframe/chart artifact implementation was found in this source. |
| Some source behavior must be inferred from partial implementation. | Runtime package metadata and some exact dependency versions are absent. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Source/product mismatch | Keep direct port and data-analyst extensions separated in traceability and implementation plans. |
| No `package.json` | Infer dependencies conservatively and verify against imports during implementation. |
| Proprietary prompt/code provenance | Recreate prompt intent and behavior without copying source text verbatim. |
| Permission/sandbox drift | Model permission policy as first-class state and add tests around side effects. |
| LangGraph loop complexity | Start with a small graph skeleton and add subgraphs incrementally. |
| MCP/plugin complexity | Implement registry abstractions before provider-specific behavior. |
| Session restore correctness | Persist graph events and test resume/rewind/compact scenarios. |
| Human confirmation UX | Use explicit pending-confirmation state and client adapters. |
| Data analyst extension scope creep | Require separate acceptance criteria before implementing extension skills. |

## Ambiguous Source Areas

| Area | Ambiguity | Current handling |
| --- | --- | --- |
| Exact dependency versions | No `package.json`. | Record imports and choose modern Python equivalents during implementation. |
| Browser app behavior | User described a React data analyst app, source is terminal React+Ink. | Treat browser UI as replacement, not direct source port. |
| Data analysis workflows | Not present as first-class source features. | Mark as optional extension. |
| General artifacts | Source has files/logs/reports, not artifact preview/edit system. | Port source outputs; design optional artifact layer separately. |
| Some prompt wording | Prompt files exist, but provenance is sensitive. | Recreate functional prompt templates without verbatim copying. |
| Duplicate candidate source tree | Two similar-size source folders exist. | Audit used path under requested `llm-data-analyst` parent. |

## Audit Gate Checklist

| Gate item | Status | Evidence |
| --- | --- | --- |
| `SOURCE_AUDIT.md` created | pass | `docs/SOURCE_AUDIT.md` |
| `SKILLS_AUDIT.md` created | pass | `docs/SKILLS_AUDIT.md` |
| `FEATURE_TRACEABILITY_MATRIX.md` created | pass | `docs/FEATURE_TRACEABILITY_MATRIX.md` |
| `MIGRATION_SPEC.md` created | pass | this file |
| All key source files reviewed | pass | Key entries, services, tools, skills, prompts, commands, UI screens, hooks, config, and storage files are listed in `SOURCE_AUDIT.md`. |
| `package.json` analyzed | pass | Search found no `package.json`; this absence and its implications are documented. |
| Prompts found and described | pass | Prompt locations and categories are listed in `SOURCE_AUDIT.md` and this spec. |
| State management described | pass | State is described across app state, query state, config state, session state, permission state, and derived UI state in `SOURCE_AUDIT.md`. |
| Workflows described | pass | User scenarios and workflow/orchestration files are documented in `SOURCE_AUDIT.md` and the traceability matrix. |
| Skills/capabilities/tools/actions found or absence proven | pass | `SKILLS_AUDIT.md` includes explicit skills, skill-like capabilities, tools, searches performed, and non-skills evidence. |
| Each source feature has a migration mapping | pass | `FEATURE_TRACEABILITY_MATRIX.md` maps source features to LangGraph, skill, service/tool, and status. |
| Each skill-like capability has a target | pass | `SKILLS_AUDIT.md` classifies each capability as LangGraph node/subgraph, Skill, Tool/Service, or UI layer. |
| No unclear feature lacks an explicit assumption | pass | Ambiguities are recorded in `SOURCE_AUDIT.md`, `FEATURE_TRACEABILITY_MATRIX.md`, and this spec. |

## Implementation Boundary

The audit gate is satisfied by documentation only. Implementation should start only in a later phase after the user accepts this audit and resolves the source/product mismatch if necessary.
