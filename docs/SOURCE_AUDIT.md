# Source Audit

## Audit Scope

Requested source path: `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-like-project`

Actual path status:

- `llm-data-analyst\claude-like-project` was not present.
- The closest existing source tree is `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project`.
- A second matching copy exists at `C:\Users\dimka\Documents\PROJECTS\claude-code-like-project`.
- Both candidate trees contain 1905 tracked source files by `rg --files`.

Audit assumption: this audit uses `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project` because it is the closest real path under the requested `llm-data-analyst` directory.

Important mismatch: the audited source is not a React web data analyst application. It is a TypeScript/Bun React+Ink terminal application modeled on Claude Code. README describes it as a Claude Code source dump/leaked-source reconstruction. This affects the migration: a faithful port can preserve CLI/chat/tool/skill/session behavior, but CSV/Excel/Parquet data-analysis workflows, chart artifacts, and web data analyst UI are not present as first-class features in this source.

Provenance risk: because README identifies the source as leaked/reconstructed, the migration must avoid copying proprietary prompts/code verbatim. Prompts and behaviors should be reimplemented from audited intent and public/product requirements.

## Package and Dependency Audit

`package.json` was searched in both candidate source trees with:

- `rg --files -g package.json`
- recursive `Get-ChildItem -Recurse -Filter package.json`

Result: no `package.json` is present in the audited tree.

Dependencies are inferred from README and imports:

- Runtime/build: Bun, TypeScript.
- UI: React + Ink terminal renderer.
- CLI: Commander style parser.
- Validation: Zod.
- LLM provider: Anthropic SDK and API wrappers.
- Search: ripgrep through GrepTool.
- MCP: Model Context Protocol client/server transports.
- Storage: JSON/JSONL files under Claude config directories.
- System integrations: keychain/OAuth, git, shell, LSP, IDE bridge, terminal, optional voice.
- Telemetry: OpenTelemetry/Datadog/GrowthBook-like feature flags.

Migration note: the Python/LangGraph version must explicitly define dependencies in a new Python project because the source tree does not provide Node package metadata.

## Top-Level Structure

Root files:

| Path | Purpose | Migration role |
| --- | --- | --- |
| `README.md` | High-level architecture and feature overview. Also states the source provenance. | Source of architectural inventory only; do not copy implementation text. |
| `LEARNING_PATH.md`, `LEARNING_PATH.pdf` | Learning guide/reference for this source. | Background only. |
| `src/` | Application source. | Main source for behavior mapping. |

`src/` directory inventory:

| Directory | Observed role | Migration replacement |
| --- | --- | --- |
| `entrypoints/` | CLI/SDK/daemon/native entrypoints. | Python CLI/FastAPI entrypoints plus LangGraph runtime bootstrap. |
| `main.tsx` | Main command parser, setup, startup orchestration, command registration, option handling. | Python bootstrap layer and CLI parser. |
| `replLauncher.tsx` | Dynamic App/REPL launcher. | Python app runner or API session runner. |
| `screens/` | Ink screens: REPL, resume picker, doctor. | UI/API layer; non-core workflow behavior becomes services. |
| `components/` | Ink components for messages, dialogs, permissions, prompts, selectors, exports, context visualization. | UI layer replacement. |
| `hooks/` | React hooks for input, permissions, queues, tools, sessions, notifications, IDE/remote/plugin behavior. | Split into UI adapters and backend services. |
| `state/` | React app state store and default app state. | LangGraph state schema plus UI session state. |
| `commands/` | Slash command implementations and command metadata. | Command registry plus LangGraph command-router nodes. |
| `tools/` | Tool implementations callable by the model. | Python tools/services with permission wrappers. |
| `skills/` | Skill loader, bundled skills, MCP skill builders. | Python SkillRegistry and skill prompt templates. |
| `services/` | API, MCP, compacting, analytics, tools orchestration, memory, notifications. | Python service layer. |
| `utils/` | Files, sessions, config, permissions, prompts, messages, plugins, git, shell, MCP helpers. | Python utilities/services. |
| `bridge/`, `remote/`, `server/`, `upstreamproxy/` | Remote session, bridge, server/proxy behavior. | Optional remote/session API layer. |
| `plugins/` | Built-in plugin registry scaffolding. | Plugin registry abstraction. |
| `context/` | React contexts such as voice/overlay/notifications/stats. | UI-only state providers. |
| `memdir/`, `services/SessionMemory`, `services/extractMemories` | Memory files and memory extraction prompts/workflows. | Memory service and LangGraph memory nodes. |
| `tasks/` | Local/remote/background task models and helpers. | Task service and agent/task graph. |
| `schemas/`, `types/` | Zod schemas and TypeScript type models. | Pydantic models. |
| `ink/`, `keybindings/`, `vim/`, `voice/` | Terminal UI, keybindings, input modes, optional voice. | UI replacement; not LangGraph core. |

## Entrypoints

| File | Purpose | Key exports/behavior | Product role | Migration plan |
| --- | --- | --- | --- | --- |
| `src/entrypoints/cli.tsx` | Fast bootstrap entrypoint. | Sets env defaults; handles fast-path flags (`--version`, prompt dump, MCP/native host/daemon/remote/template/update/bare paths); imports `main.js`. | Starts CLI quickly and routes special modes before full app load. | Replace with Python CLI bootstrap and lightweight pre-parser. |
| `src/main.tsx` | Full CLI parser and application initializer. | `main()`, deferred prefetches, Commander options and subcommands, auth/model/MCP/plugin/session setup, REPL launch, SDK/headless modes. | Product shell: interactive chat, headless query, auth, MCP, plugins, tasks, server, doctor/update/export. | Split into Python CLI, settings loader, provider initialization, tool/command registry, and LangGraph session startup. |
| `src/replLauncher.tsx` | Dynamic renderer launcher. | `launchRepl(root, appProps, replProps, renderAndRun)`. | Loads `<App><REPL /></App>` for interactive sessions. | Replace with web/API session creation or terminal runner. |
| `src/entrypoints/sdk/coreSchemas.ts` | SDK serializable schemas. | Zod schemas for usage, output format, MCP config/status, permissions, hooks, prompt requests, agents, SDK messages/results. | Contract for SDK/headless clients. | Replace with Pydantic DTOs/OpenAPI schemas. |

## Core Workflow Files

| File | Purpose | Key exported functions/types | Product role | Migration plan |
| --- | --- | --- | --- | --- |
| `src/commands.ts` | Central command registry. | `getCommands`, `getSkillToolCommands`, `getSlashCommandToolSkills`, safe command sets, command filtering. | Builds slash command surface, builtin commands, dynamic skills, plugin commands, workflow commands. | Python `CommandRegistry`; LangGraph command routing node. |
| `src/types/command.ts` | Command model. | `Command`, `PromptCommand`, `LocalCommand`, `LocalJSXCommand`, `CommandBase`. | Defines prompt skills, local commands, UI commands and metadata. | Pydantic command model. |
| `src/tools.ts` | Tool registry. | `getAllBaseTools`, `getTools`, `assembleToolPool`. | Collects built-in, MCP, feature-gated, and simple-mode tools. | Python `ToolRegistry` and graph tool selection node. |
| `src/Tool.ts` | Tool interface and permission context. | `Tool`, `ToolUseContext`, `ToolPermissionContext`, `buildTool`, tool result/progress types. | Core contract for all model-callable tools. | Python base tool protocol, Pydantic schemas, permission wrapper. |
| `src/QueryEngine.ts` | Headless/SDK query engine. | `QueryEngineConfig`, `QueryEngine`, `submitMessage()`. | Manages session messages, system prompt building, query loop, SDK output. | LangGraph session graph facade. |
| `src/query.ts` | Main async LLM/tool loop. | `query()`, `queryLoop`, streaming event flow, compaction triggers, tool execution scheduling. | Core orchestration for model streaming, tool-use, retries, auto-compact, hooks. | LangGraph main graph: model node, tool router, compaction, error/retry, persistence. |
| `src/services/tools/toolOrchestration.ts` | Tool scheduling. | `runTools`. | Groups concurrent/read-only tool calls and serializes unsafe calls. | Python tool executor service with concurrency policy. |
| `src/services/tools/toolExecution.ts` | Tool execution lifecycle. | `runToolUse`, tool classification/error helpers. | Runs one tool call with permissions, hooks, telemetry, result storage/truncation. | Python tool execution node/service. |

## UI and React Components

The source is a terminal UI built with React+Ink, not a browser React app.

Important UI files:

| File | Purpose | Key exports/components | Role | Migration |
| --- | --- | --- | --- | --- |
| `src/components/App.tsx` | Top-level provider wrapper. | `App`. | Provides app state, stats, FPS contexts. | UI-only replacement. |
| `src/screens/REPL.tsx` | Main interactive terminal screen. | `REPL`, `Props`. | Owns chat UI, input submission, message rendering, tool confirmations, resume, compaction, queues, session end hooks. | Split into API/session controller plus LangGraph runtime; terminal-specific UI removed/replaced. |
| `src/screens/ResumeConversation.tsx` | Resume picker screen. | `ResumeConversation`. | Lets user select previous sessions. | API/UI resume endpoint plus storage queries. |
| `src/screens/Doctor.tsx` | Diagnostic screen. | `Doctor`. | Health checks and diagnostics. | Python diagnostic command/service. |
| `src/components/Messages.tsx` | Message list rendering. | `Messages`, grouping/filter helpers. | Renders conversation, tool results, attachments, compaction boundaries. | UI-only renderer; backend keeps message model. |
| `src/components/PromptInput/PromptInput.tsx` | Main prompt input. | default `PromptInput`. | Text input, paste, mode hints, typeahead, queued commands. | UI-only; backend keeps input-normalization service. |
| `src/components/messages/*` | Per-message renderers. | Assistant/user/system/tool/attachment/error/rate-limit/plan components. | Display layer for chat states. | UI replacement. |
| `src/components/permissions/*` | Permission dialogs. | `PermissionRequest`, `BashPermissionRequest`, `FileEditPermissionRequest`, `ExitPlanModePermissionRequest`, etc. | User approval UX for tool calls. | UI/API confirmation endpoints plus permission service. |
| `src/components/ExportDialog.tsx` | Export dialog. | `ExportDialog`. | Copy/save conversation transcript. | API/UI export action. |
| `src/components/ContextVisualization.tsx` | Context usage visualization. | `ContextVisualization`. | Shows token/context breakdown and compaction/collapse state. | Optional UI replacement; backend `analyze_context` service. |
| `src/components/skills/SkillsMenu.tsx` | Skills listing UI. | `SkillsMenu`. | Displays available skills. | UI replacement over `SkillRegistry`. |

## Hooks

Hooks are mostly React UI adapters around backend concerns. Important hooks:

| File/pattern | Purpose | Migration |
| --- | --- | --- |
| `src/hooks/useCanUseTool.tsx` | Builds `CanUseToolFn` by consulting permission rules and UI confirmation queues. | Backend `PermissionService` plus UI confirmation adapter. |
| `src/hooks/toolPermission/handlers/interactiveHandler.ts` | Interactive permission flow with local UI, bridge/channel, hooks, classifiers. | LangGraph permission gate node and async confirmation service. |
| `src/hooks/useMergedTools.ts`, `useMergedCommands.ts`, `useMergedClients.ts` | Merge static, MCP, plugin, and session-provided surfaces. | Registry composition services. |
| `src/hooks/useQueueProcessor.ts`, `useCommandQueue.ts` | Queued input/commands while a turn is running. | Session queue service. |
| `src/hooks/useLogMessages.ts` | Transcript logging/persistence integration. | Storage writer service. |
| `src/hooks/useSkillsChange.ts`, `useManagePlugins.ts` | Skill/plugin hot reload management. | Registry reload service. |
| `src/hooks/useRemoteSession.ts`, `useReplBridge.tsx`, `useMailboxBridge.ts` | Remote/bridge session synchronization. | Optional remote API/session sync. |
| `src/hooks/useIDEIntegration.tsx`, `useIdeSelection.ts`, `useIdeLogging.ts` | IDE connection, selection, and logging. | Optional IDE integration service. |
| `src/hooks/useTasksV2.ts`, `useTaskListWatcher.ts` | Task state observation. | Task service/API. |
| `src/hooks/useArrowKeyHistory.tsx`, `usePasteHandler.ts`, `useTypeahead.tsx`, `useVimInput.ts` | Input ergonomics. | UI-only unless web terminal keeps same UX. |
| `src/hooks/notifs/*` | Notification surfaces. | UI-only plus backend event stream. |

## API Calls and Provider Layer

| File | Purpose | Key behavior | Migration |
| --- | --- | --- | --- |
| `src/services/api/client.ts` | Anthropic client construction. | Supports direct API keys/tokens, OAuth, Bedrock, Vertex, Foundry, custom headers, timeouts, base URLs, certificates/proxy. | Python model provider abstraction with provider-specific clients. |
| `src/services/api/claude.ts` | Claude API call wrapper. | Converts messages/tools/system prompt, streaming/non-streaming calls, prompt caching, betas, thinking, structured output, tool search, retry/cost telemetry. | LangGraph model node service. |
| `src/services/api/withRetry.ts` | Retry and fallback behavior. | Provider-aware retry/fallback handling. | Python retry policy. |
| `src/services/api/filesApi.ts` | Public Files API integration. | `downloadFile`, `downloadAndSaveFile`, `downloadSessionFiles`, `uploadFile`; session upload directory; retry/backoff; size limits. | File transfer service if remote attachments are retained. |
| `src/services/api/dumpPrompts.ts` | Prompt dump support. | Used by prompt dump flag. | Dev/debug endpoint. |
| `src/services/api/usage.ts`, `cost-tracker.ts` | Usage/cost tracking. | Model usage and cost state. | Usage/cost service. |

## Prompts

Prompt locations found:

| Path | Prompt role | Migration |
| --- | --- | --- |
| `src/constants/prompts.ts` | Main system prompt builder. Includes tool usage policy, language/output style, MCP, skills, scratchpad, proactive mode, environment details. | Recreate as Python prompt templates from behavior, not verbatim copy. |
| `src/tools/*/prompt.ts` | Per-tool prompt descriptions for Bash, Read, Write, Edit, WebFetch, WebSearch, Agent, Skill, Todo, PlanMode, etc. | Tool-specific prompt templates. |
| `src/tools/SkillTool/prompt.ts` | Skill execution prompt and skill listing budget logic. | Skill selection/execution prompt template. |
| `src/services/compact/prompt.ts` | Full and partial conversation compaction prompts. | LangGraph compaction/summarization node prompt. |
| `src/services/extractMemories/prompts.ts` | Memory extraction subagent prompts. | Memory extraction subgraph prompt. |
| `src/services/SessionMemory/prompts.ts` | Session notes/memory update prompts and optional custom prompt file. | Session memory node prompt. |
| `src/skills/bundled/*.ts` | Bundled skill prompts. | Skill prompt templates. |
| `src/tools/AgentTool/built-in/*` | Built-in agent prompts. | Agent/subgraph definitions. |

Prompt migration warning: the audited source contains proprietary/reconstructed prompt text. The Python version should preserve behavior and categories, not copy long prompt wording.

## Models, Types, and Schemas

| Source | Types/schemas | Migration |
| --- | --- | --- |
| `src/Tool.ts` | Tool protocol, input JSON schema, output schema, permission/tool contexts, progress, result mapping. | Pydantic tool protocol and runtime context. |
| `src/types/command.ts` | Command/slash-command/skill model. | Pydantic command model. |
| `src/types/permissions.ts` | Permission modes/rules/updates/decisions. | Permission DTOs and storage models. |
| `src/types/logs.ts` | Serialized transcript/log metadata, session titles, worktree state, content replacements, attribution. | Storage DTOs and migration-compatible JSONL format. |
| `src/types/plugin.ts` | Plugin manifests, loaded plugin, plugin errors, components. | Plugin DTOs. |
| `src/types/hooks.ts` | Hook input/output types. | Hook DTOs. |
| `src/types/ids.ts` | Session/agent id branding. | UUID/newtype wrappers. |
| `src/entrypoints/sdk/coreSchemas.ts` | SDK Zod schemas for usage, config, permissions, hooks, agents, messages/results. | Pydantic/OpenAPI schemas. |
| `src/schemas/hooks.ts` | Hook schemas. | Pydantic hook schemas. |

Source incompleteness: many modules import `src/types/message.js` and related generated message queue types, but `src/types/message.ts` is not present in the audited file list. The actual message schema must be inferred from imports/usages or recovered before exact binary-compatible migration.

## Application State

State files:

| File | Purpose | Migration |
| --- | --- | --- |
| `src/state/store.ts` | Minimal external store with `getState`, `setState`, `subscribe`. | Python session state store or API state manager. |
| `src/state/AppStateStore.ts` | Large `AppState` type and `getDefaultAppState()`. | LangGraph state schema plus UI session state. |
| `src/state/AppState.tsx` | React context provider and selectors. | UI-only adapter. |
| `src/state/onChangeAppState.ts` | App state change side effects. | Event hooks/watchers. |
| `src/bootstrap/state.ts` | Process-global session/runtime state: session id, cwd, costs, tool stats, plugin/channel state, invoked skills, compaction flags. | Runtime context and graph/session metadata service. |

Core AppState areas:

- Settings/theme/verbose/model/effort/thinking.
- Permission context, allowed/denied/ask rules, additional directories.
- MCP clients/tools/resources/commands and dynamic MCP config.
- Plugins, agent definitions, enabled tools/commands.
- File history, attribution, todos/tasks.
- Notifications and overlays.
- Remote/bridge/team/teammate state.
- Elicitation, prompt requests, skill improvement survey.
- Browser/computer-use/repl optional state.
- Fast mode/advisor/proactive flags.

Migration mapping:

- LangGraph state should store: `messages`, `session_id`, `project_root`, `cwd`, `model`, `provider`, `permission_context`, `tool_registry_snapshot`, `skill_registry_snapshot`, `mcp_state`, `memory_state`, `task_state`, `file_history`, `content_replacements`, `cost_usage`, `pending_confirmations`, `errors`, `ui_events`.
- UI-only flags should stay outside the core graph.

## User Workflows

### Interactive chat

Flow:

1. `src/main.tsx` parses CLI and launches REPL.
2. `src/replLauncher.tsx` renders App + REPL.
3. `src/screens/REPL.tsx` collects user input and calls `handlePromptSubmit`.
4. `src/utils/handlePromptSubmit.ts` and `src/utils/processUserInput/*` normalize input, slash commands, attachments, agents, hooks.
5. `src/query.ts` streams model output and tool events.
6. `src/services/tools/*` executes tools through permissions and hooks.
7. `src/screens/REPL.tsx` appends messages, renders state, logs transcripts.

LangGraph equivalent: input normalization node -> slash/command router -> system context builder -> LLM node -> tool router -> permission gate -> tool executor -> post-tool hooks -> compaction check -> persistence -> response event stream.

### Headless/SDK query

Flow:

- `main.tsx` handles `-p/--print`, `--output-format`, `--input-format`, JSON schema, max turns/budget.
- `QueryEngine.ts` wraps the same model/tool loop without Ink UI.
- `entrypoints/sdk/coreSchemas.ts` defines serializable message/result contracts.

LangGraph equivalent: API/SDK facade over the same graph, with stream events and result DTOs.

### Slash commands

Flow:

- `commands.ts` registers builtin/local/local-jsx/prompt commands.
- `processSlashCommand.tsx` parses and routes command input.
- Commands can directly mutate UI/session state, return text, or expand prompt content into the model.

Migration: command registry plus command-router node. UI commands become API/UI handlers; prompt commands become skills.

### Files and attachments

Flow:

- `utils/processUserInput/processUserInput.ts` handles pasted content, images, at-mentions, attachment messages and hooks.
- `utils/attachments.ts` builds typed attachment messages for files, PDFs, already-read files, memories, tasks, agents, hook context.
- `FileReadTool` reads text with line numbers, images, PDFs, and Jupyter notebooks.
- `FileWriteTool`, `FileEditTool`, `NotebookEditTool` write/edit files with permission checks.
- `services/api/filesApi.ts` downloads/uploads remote file attachments.
- `utils/mcpOutputStorage.ts` persists large/binary MCP output as files.

Migration: FileService, AttachmentService, NotebookService, RemoteFilesService, MCPOutputStorage.

### Projects and sessions

Flow:

- `bootstrap/state.ts` tracks original cwd, project root, cwd state, session id.
- `utils/sessionStorage.ts` stores transcripts as JSONL under config project directories.
- `commands/resume` and `screens/ResumeConversation.tsx` list/select/restore sessions.
- `sessionRestore.ts` restores messages, file history, attribution, agent settings, worktree state, content replacements.
- `/session`, `/rename`, `/tag`, `/branch`, `/export`, `/clear`, `/compact`, `/rewind` mutate session metadata or history.

Migration: SessionStorage service backed by JSONL or SQLite; resume graph bootstrap.

### Artifacts

No general artifact system comparable to web chat artifacts was found.

Observed artifact-adjacent behavior:

- `entrypoints/sdk/coreSchemas.ts` contains an `artifact_urls` field in SDK result schemas.
- `/export` saves/copies rendered conversation text.
- `mcpOutputStorage.ts` and `toolResultStorage.ts` persist large/binary tool results.
- File tools create/edit project files and notebooks.
- `commands/insights.ts` generates a standalone HTML insights report from usage logs.

Migration: keep transcript export and tool-output persistence. If the target product requires web artifacts, that is a new feature, not a direct source port.

### Data analysis and visualizations

No first-class data analyst workflow was found.

Observed adjacent support:

- `FileReadTool` can read Jupyter notebooks and returns cells/outputs/visualizations.
- `NotebookEditTool` can edit notebooks.
- `BashTool`/`PowerShellTool` can run user commands, so data analysis could happen through shell/Python if available.
- `commands/insights.ts` analyzes Claude Code session logs and generates HTML charts.
- `ContextVisualization.tsx` visualizes token/context usage.
- File type constants mention `.csv`, `.xls`, `.xlsx`; `mcpOutputStorage.ts` maps CSV/XLSX mime types to saved files.
- No Parquet support was found.
- Search terms produced `parquet: 0` files and `analyst: 0` files.

Migration: do not claim direct CSV/Excel/Parquet/pandas/chart artifact features. If the Python/LangGraph target must be a data analyst app, add those as new requirements after audit.

### Export/download

Flow:

- `/export` (`src/commands/export/export.tsx`) renders messages through `exportRenderer.tsx`, then writes `.txt` or opens `ExportDialog`.
- `ExportDialog.tsx` supports clipboard or save to file.
- `services/api/filesApi.ts` downloads/uploads remote Files API attachments.
- `commands/insights.ts` can build/export an HTML report.

Migration: ExportService for transcripts; optional report export; remote file transfer service.

## Config and Environment

Important config sources:

- CLI options in `main.tsx`.
- Global/project settings in `utils/config.ts`.
- Secure storage/OAuth/keychain helpers.
- `.claude` directories for settings, commands, skills, sessions, MCP, memory.
- Environment variables.

Key env/config variables observed:

| Category | Variables/examples |
| --- | --- |
| Config roots | `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_MANAGED_SETTINGS_PATH` |
| Provider/auth | `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_CUSTOM_HEADERS`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `ANTHROPIC_DEFAULT_*_MODEL` |
| Bedrock/Vertex/Foundry | `CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_BEARER_TOKEN_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`, `CLAUDE_CODE_USE_FOUNDRY`, `ANTHROPIC_FOUNDRY_API_KEY` |
| Runtime mode | `CLAUDE_CODE_REMOTE`, `CLAUDE_CODE_SIMPLE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_REMOTE_SESSION_ID`, `CLAUDE_CODE_ACTION` |
| Model/thinking | `CLAUDE_CODE_EFFORT_LEVEL`, `MAX_THINKING_TOKENS`, `CLAUDE_CODE_DISABLE_THINKING`, `CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` |
| Compaction/context | `DISABLE_COMPACT`, `DISABLE_AUTO_COMPACT`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `API_MAX_INPUT_TOKENS`, `API_TARGET_INPUT_TOKENS` |
| Tools | `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`, `BASH_MAX_OUTPUT_LENGTH`, `CLAUDE_CODE_GLOB_TIMEOUT_SECONDS`, `CLAUDE_CODE_DISABLE_ATTACHMENTS` |
| Plugins/skills | `CLAUDE_CODE_PLUGIN_CACHE_DIR`, `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS`, `CLAUDE_CODE_DISABLE_POLICY_SKILLS` |
| Remote/bridge | `CLAUDE_BRIDGE_BASE_URL`, `CLAUDE_BRIDGE_OAUTH_TOKEN`, `CLAUDE_BRIDGE_SESSION_INGRESS_URL`, `CLAUDE_CODE_SESSION_ACCESS_TOKEN` |
| Telemetry/flags | `USER_TYPE`, `NODE_ENV`, `CLAUDE_CODE_ENABLE_TELEMETRY`, `OTEL_*`, `CLAUDE_CODE_GB_BASE_URL` |

Feature flags via `feature(...)` are pervasive. Examples include `PROACTIVE`, `KAIROS`, `BRIDGE_MODE`, `DAEMON`, `VOICE_MODE`, `AGENT_TRIGGERS`, `AGENT_TRIGGERS_REMOTE`, `MONITOR_TOOL`, `WEB_BROWSER_TOOL`, `EXPERIMENTAL_SKILL_SEARCH`, `MCP_SKILLS`, `CONTEXT_COLLAPSE`, `CACHED_MICROCOMPACT`, `TEAMMEM`, `BUDDY`, `FORK_SUBAGENT`, `WORKFLOW_SCRIPTS`.

Migration: use explicit Python settings with typed config and feature flags, not scattered env reads inside graph nodes.

## Layer Classification

UI-only:

- `components/*`, most `hooks/*`, `screens/*`, `ink/*`, `keybindings/*`, `vim/*`, `voice/*`, terminal-specific export dialogs and notification components.

Workflow/orchestration:

- `main.tsx`, `QueryEngine.ts`, `query.ts`, `commands.ts`, `tools.ts`, `processUserInput/*`, `processSlashCommand.tsx`, `services/tools/*`, compaction services, session restore.

Business logic:

- Tool semantics (`BashTool`, file tools, web tools, MCP tools, task/todo tools, skills, agents, permissions, session storage, memory extraction, plugin loading).

Low-level utilities:

- `utils/file*`, `utils/sessionStorage.ts`, `utils/config.ts`, `utils/permissions/*`, `utils/messages*`, `utils/notebook.ts`, `utils/pdf*`, `utils/mcp*`, `utils/git*`, `utils/envUtils.ts`, `utils/model/*`, `utils/plugin*`.

## Important Files Reviewed

| Path | Purpose | Key exports/classes/components | Product role | Port/replacement |
| --- | --- | --- | --- | --- |
| `README.md` | Architecture overview and source provenance. | N/A. | Confirms CLI/tool/skill/plugin architecture. | Audit input only. |
| `src/entrypoints/cli.tsx` | Fast CLI bootstrap. | top-level routing. | Pre-main fast paths. | Python bootstrap pre-parser. |
| `src/main.tsx` | Main CLI app. | `main`, `startDeferredPrefetches`. | All startup/subcommands/options. | Python CLI/API bootstrap. |
| `src/replLauncher.tsx` | REPL render launcher. | `launchRepl`. | Starts interactive UI. | UI/API session runner. |
| `src/screens/REPL.tsx` | Main chat UI/controller. | `REPL`. | Interactive session controller. | LangGraph session controller plus UI. |
| `src/commands.ts` | Command registry. | `getCommands`, `getSkillToolCommands`, `findCommand`. | Slash commands and skill inclusion. | `CommandRegistry`. |
| `src/types/command.ts` | Command types. | `Command`, `PromptCommand`, `LocalCommand`. | Command/skill contract. | Pydantic schemas. |
| `src/tools.ts` | Tool registry. | `getTools`, `assembleToolPool`. | Built-in/MCP tool surface. | `ToolRegistry`. |
| `src/Tool.ts` | Tool protocol. | `Tool`, `ToolUseContext`, `buildTool`. | Tool contract and permissions context. | Tool base class/protocol. |
| `src/query.ts` | Model/tool loop. | `query`. | Core orchestration. | LangGraph graph. |
| `src/QueryEngine.ts` | Headless query engine. | `QueryEngine`. | SDK/noninteractive runtime. | Graph facade. |
| `src/services/tools/toolOrchestration.ts` | Tool batching. | `runTools`. | Concurrency and ordering. | Tool executor. |
| `src/services/tools/toolExecution.ts` | Tool execution. | `runToolUse`. | Permission/hook/result lifecycle. | Tool execution node. |
| `src/hooks/useCanUseTool.tsx` | Permission hook. | default `useCanUseTool`. | UI permission decision integration. | Permission service + adapter. |
| `src/utils/permissions/permissions.ts` | Permission rules engine. | `hasPermissionsToUseTool`, `getAllowRules`, `getDenyRules`, `getAskRules`. | Tool access control. | Permission service. |
| `src/state/AppStateStore.ts` | App state model. | `AppState`, `getDefaultAppState`. | Runtime/session/UI state. | LangGraph state + UI state. |
| `src/bootstrap/state.ts` | Global runtime state. | session/cwd/cost/tool/skill state helpers. | Process/session metadata. | Runtime context service. |
| `src/constants/prompts.ts` | System prompt builder. | `getSystemPrompt`, `DEFAULT_AGENT_PROMPT`. | Model behavior contract. | Prompt templates. |
| `src/services/api/client.ts` | API client factory. | client construction helpers. | Provider/auth config. | Provider service. |
| `src/services/api/claude.ts` | LLM API wrapper. | query/model call helpers. | Model streaming and tool schema conversion. | Model node. |
| `src/utils/sessionStorage.ts` | Transcript storage. | transcript path/load/save helpers. | Session persistence/resume. | Storage layer. |
| `src/utils/config.ts` | Config models/storage. | `GlobalConfig`, `ProjectConfig`, getters/savers. | Settings and project state. | Config service. |
| `src/utils/processUserInput/processUserInput.ts` | User input normalization. | `processUserInput`. | Attachments/slash commands/hooks. | Input node. |
| `src/utils/processUserInput/processSlashCommand.tsx` | Slash command routing. | slash command processor. | Command execution path. | Command router node. |
| `src/utils/attachments.ts` | Attachment creation/discovery. | attachment types/helpers. | Files/memory/tasks/agent mentions. | Attachment service. |
| `src/services/api/filesApi.ts` | Files API. | `downloadSessionFiles`, `uploadFile`. | Remote file attachments. | File transfer service. |
| `src/tools/FileReadTool/FileReadTool.ts` | Read tool. | `FileReadTool`, `registerFileReadListener`. | Reads text/images/PDF/notebooks. | File read service/tool. |
| `src/tools/FileReadTool/prompt.ts` | Read tool prompt. | `renderPromptTemplate`. | Tool instructions. | Tool prompt template. |
| `src/tools/NotebookEditTool/NotebookEditTool.ts` | Notebook editing. | `NotebookEditTool`. | Jupyter notebook writes. | Notebook service/tool. |
| `src/skills/loadSkillsDir.ts` | Skill loader. | `getSkillDirCommands`, `createSkillCommand`, dynamic/conditional skills. | File-based skills and legacy command loading. | Skill registry. |
| `src/skills/bundledSkills.ts` | Bundled skill registry. | `registerBundledSkill`, `getBundledSkills`. | Built-in skills. | Built-in Skill definitions. |
| `src/tools/SkillTool/SkillTool.ts` | Skill executor. | `SkillTool`, forked skill execution helpers. | Model invokes skills. | Skill execution node/subgraph. |
| `src/tools/SkillTool/prompt.ts` | Skill prompt/listing. | `getPrompt`, `formatCommandsWithinBudget`. | Skill discovery/invocation instructions. | Skill prompt template. |
| `src/services/compact/prompt.ts` | Compact prompts. | `getCompactPrompt`, `getPartialCompactPrompt`. | Conversation summarization. | Compaction node. |
| `src/services/extractMemories/prompts.ts` | Memory prompts. | `buildExtractAutoOnlyPrompt`, `buildExtractCombinedPrompt`. | Persistent memory extraction. | Memory extraction subgraph. |
| `src/components/ExportDialog.tsx` | Export UI. | `ExportDialog`. | Copy/save transcript. | UI export adapter. |
| `src/commands/export/export.tsx` | Export command. | `call`, `extractFirstPrompt`, `sanitizeFilename`. | Transcript export. | Export service/command. |
| `src/utils/exportRenderer.tsx` | Static message renderer. | `renderMessagesToPlainText`, `streamRenderedMessages`. | Export rendering. | Backend renderer or plain text serializer. |
| `src/commands/insights.ts` | Usage insights report. | report builders/export types. | Session analytics HTML charts. | Optional report service. |
| `src/plugins/builtinPlugins.ts` | Built-in plugin registry. | `registerBuiltinPlugin`, `getBuiltinPlugins`. | Plugin-provided skills/hooks/MCP. | Plugin registry. |
| `src/types/plugin.ts` | Plugin models. | `BuiltinPluginDefinition`, `LoadedPlugin`, `PluginError`. | Plugin contract. | Pydantic plugin models. |

## Audit Conclusions

- The audited source is a Claude Code-like terminal coding assistant, not a web data analyst application.
- Its core transferable behavior is chat + tool calling + permissions + file/project/session management + skills/plugins/MCP + compaction/memory + export.
- Explicit skills exist and are central to behavior.
- Tool-like and skill-like capabilities are broad and must be preserved.
- General web artifacts and data analyst workflows are not present as first-class source features.
- New Python/LangGraph architecture must be a behavior-preserving reimplementation, not a direct line-by-line port.
