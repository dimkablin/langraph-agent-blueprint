# Skills Audit

## Audit Scope and Evidence

The source contains explicit skills and several skill-like concepts.

Searches performed:

- `rg -n -i "skill|skills|capabilit|tool|action|command|ability|plugin|workflow|artifact|data operation|analyst|chart|visuali[sz]|export|download|upload|csv|excel|parquet|data analysis|file operation" ...`
- focused searches for `registerBundledSkill`, `SkillTool`, `SKILL.md`, `mcp skills`, `workflow`, `artifact`, `csv`, `excel`, `parquet`, `chart`, `visualization`, `export`, `upload`, `download`.
- source file inspection in `src/skills`, `src/tools/SkillTool`, `src/commands.ts`, `src/tools.ts`, `src/services/mcp`, `src/utils/attachments.ts`, file tools, export, sessions, memory, and compaction.

Approximate file-count evidence from case-insensitive term search excluding source-map-heavy `tsx/js` output:

| Term | Files matched |
| --- | ---: |
| `skill` | 142 |
| `capability` | 25 |
| `tool` | 571 |
| `action` | 282 |
| `command` | 513 |
| `ability` | 114 |
| `plugin` | 169 |
| `workflow` | 64 |
| `artifact` | 20 |
| `chart` | 7 |
| `visualization` | 8 |
| `export` | 1332 |
| `download` | 44 |
| `upload` | 37 |
| `csv` | 8 |
| `excel` | 4 |
| `parquet` | 0 |
| `analyst` | 0 |
| `analysis` | 45 |

Conclusion: skills are not absent. They are explicit (`src/skills/*`) and also represented as command/tool/plugin/MCP prompt concepts.

## Explicit Skill System

| Source file | What was found | Migration meaning |
| --- | --- | --- |
| `src/skills/loadSkillsDir.ts` | Loads `skill-name/SKILL.md` from managed/user/project/additional `.claude/skills`; parses frontmatter; supports arguments, allowed tools, model override, effort, hooks, path-conditional activation, shell injection for local skills, dynamic skills, legacy `.claude/commands`. | Directly becomes Python `SkillRegistry`, `SkillDefinition`, `SkillLoader`, and conditional skill activation. |
| `src/skills/bundledSkills.ts` | Registers bundled skills with metadata and lazy extraction of bundled reference files. | Built-in skill registration in Python. |
| `src/skills/bundled/index.ts` | Initializes bundled skills: update-config, keybindings-help, verify, debug, lorem-ipsum, skillify, remember, simplify, batch, stuck, feature-gated loop/schedule/claude-api/claude-in-chrome. | Built-in Skill package. |
| `src/skills/mcpSkillBuilders.ts` | Write-once registry exposing skill command builders to MCP skill discovery without import cycles. | MCP skill adapter. |
| `src/tools/SkillTool/SkillTool.ts` | Executes skills, including forked sub-agent execution, usage tracking, MCP skills, plugin skill telemetry, permission rules. | LangGraph Skill invocation node/subgraph. |
| `src/tools/SkillTool/prompt.ts` | Skill discovery prompt, budgeted skill listing, instruction that matching skills are blocking requirements. | Skill selection prompt template. |
| `src/commands/skills/skills.tsx` | UI menu for available skills. | UI-only skill browser. |

## Bundled Skills

Observed bundled skill files:

- `batch`
- `claude-api`
- `claude-api-content`
- `claude-in-chrome`
- `debug`
- `keybindings-help`
- `loop`
- `lorem-ipsum`
- `remember`
- `schedule`
- `simplify`
- `skillify`
- `stuck`
- `update-config`
- `verify`

Some are feature-gated and may not be registered in all runtimes.

Migration rule: keep names where possible for traceability. If a bundled skill is not relevant to the final product surface, mark it as disabled/optional rather than silently dropping it.

## Classification Table

| Source concept | Source file(s) | What it does | Input | Output | Side effects | Should become LangGraph node? | Should become Skill? | Should become Tool/Service? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| File-based skills (`SKILL.md`) | `src/skills/loadSkillsDir.ts` | Loads reusable markdown capabilities with frontmatter and prompts. | Skill directories, frontmatter, args, cwd. | `PromptCommand` definitions. | Reads files; may execute local shell snippets in prompt expansion. | Yes, invocation path. | Yes. | SkillRegistry service. | Preserve `allowed-tools`, `model`, `effort`, `context`, `agent`, `paths`, hooks. |
| Legacy commands-as-skills | `src/skills/loadSkillsDir.ts`, `.claude/commands` loader | Treats markdown commands as prompt skills. | Markdown command files, args. | Prompt command. | Reads project/user config. | Yes. | Yes. | Skill/Command loader. | Mark as backward compatibility. |
| Bundled skill registry | `src/skills/bundledSkills.ts`, `src/skills/bundled/*` | Registers built-in prompt capabilities. | Code-defined skill metadata and prompt builders. | `Command` entries. | May extract reference files to temp/bundled root. | Yes for invocation. | Yes. | Skill package service. | Avoid copying proprietary prompt text verbatim. |
| MCP skills | `src/services/mcp/client.ts`, `src/skills/mcpSkillBuilders.ts` | Converts MCP resources/prompts into skill commands. | MCP server resources/prompts. | MCP skill commands. | Network/process MCP calls. | Yes. | Yes. | MCP service. | Keep as optional integration. |
| Plugin skills | `src/utils/plugins/*`, `src/plugins/builtinPlugins.ts`, `src/types/plugin.ts` | Loads skills contributed by plugins/marketplaces. | Plugin manifests and installed plugin dirs. | Skill/command entries. | Reads plugin cache, may install/update plugins. | Yes for invocation/reload. | Yes. | Plugin service. | Built-in plugin scaffolding currently has no registered built-ins. |
| `SkillTool` | `src/tools/SkillTool/SkillTool.ts`, `prompt.ts` | Lets the model invoke a skill by name/args, including forked execution. | `{ skill, args }`, context, command registry. | Tool result with skill output/progress. | Can spawn sub-agent; records skill usage. | Yes. | No, it invokes skills. | Tool/service. | Central for preserving skill behavior. |
| Slash command registry | `src/commands.ts`, `src/types/command.ts` | Registers and filters user-invocable commands. | cwd, settings, feature flags, plugin/MCP commands. | Command list. | Reads config, loads dynamic modules. | Yes, command router. | Some prompt commands are skills. | CommandRegistry. | Not all commands are skills; local-jsx is UI. |
| Prompt commands | `src/types/command.ts`, many `src/commands/*` | Expand user command into model prompt. | command name and args. | User/assistant prompt messages. | May invoke hooks or fork agent. | Yes. | Yes when reusable capability. | Command service. | Candidate skill mapping. |
| Local commands | `src/types/command.ts`, `src/commands/*` | Execute local logic and return text or UI. | command name, args, context. | Text/JSX command result. | May mutate session/config/files. | Sometimes. | Usually no. | Command/service. | `/clear`, `/resume`, `/export`, `/context`, `/config` are workflow/UI actions. |
| Workflow commands | `src/commands.ts`, workflow feature gates | Higher-level command kind. | User command. | Workflow execution prompt/result. | Varies. | Yes. | Often. | Workflow service. | Feature-gated; inspect when implementing. |
| `BashTool` | `src/tools/BashTool/*` | Executes shell commands with parsing, permission, output limits. | command string, timeout/description. | stdout/stderr/result. | Runs local process. | Tool execution node. | No. | ShellTool service. | Low-level tool, high risk. |
| `PowerShellTool` | `src/tools/PowerShellTool/*` | Windows PowerShell execution with read-only validation and permissions. | PowerShell command. | command result. | Runs local process. | Tool execution node. | No. | ShellTool service. | Relevant on Windows. |
| File read | `src/tools/FileReadTool/*`, `src/utils/readFileInRange.ts`, `src/utils/pdf.ts`, `src/utils/notebook.ts` | Reads text with line numbers, images, PDFs, notebooks. | absolute path, offset/limit/pages. | text/image/PDF/notebook content. | Updates read file cache/listeners; may activate conditional skills. | Tool execution node. | Could be skill-like capability but better tool. | FileService. | Reads `.ipynb` with outputs/visualizations; no dataframe parsing service. |
| File write | `src/tools/FileWriteTool/*` | Creates/overwrites files. | file path and content. | write result. | Writes filesystem; file history/attribution. | Tool execution node. | No. | FileService. | Needs permission gate. |
| File edit | `src/tools/FileEditTool/*` | Replaces text in files. | file path, old/new string. | edit result/diff. | Writes filesystem; file history/attribution. | Tool execution node. | No. | FileService. | Needs prior read-like safety preserved. |
| Notebook edit | `src/tools/NotebookEditTool/*` | Edits Jupyter notebook cells. | notebook path, cell operation/content. | notebook edit result. | Writes `.ipynb`. | Tool execution node. | No. | NotebookService. | Closest data-analysis-adjacent capability. |
| Glob search | `src/tools/GlobTool/*` | File glob search. | pattern, path. | matching paths. | Reads filesystem. | Tool execution node. | No. | SearchService. | Low-level search. |
| Grep search | `src/tools/GrepTool/*` | ripgrep content search. | pattern, path, filters. | matching lines/files. | Reads filesystem/process. | Tool execution node. | No. | SearchService. | Dependency on ripgrep or Python equivalent. |
| Web fetch | `src/tools/WebFetchTool/*` | Fetches URL and optionally applies prompt to markdown. | URL, prompt. | fetched/summarized content. | Network. | Tool execution node. | No. | WebService. | Needs allowlist/blocklist/prompt injection handling. |
| Web search | `src/tools/WebSearchTool/*` | Performs web search. | query. | search results. | Network. | Tool execution node. | No. | WebService. | Current environment may restrict network; production tool separate. |
| MCP tools/resources | `src/services/mcp/client.ts`, `src/tools/MCPTool`, `ListMcpResourcesTool`, `ReadMcpResourceTool` | Connects to MCP servers, exposes tools/resources/prompts/skills. | MCP config, tool/resource requests. | tool results/resources/commands. | Network/process transports, OAuth. | Yes for routing. | MCP prompts can become skills. | MCP service. | Preserve namespacing and permission handling. |
| Tool search/deferred tools | `src/tools/ToolSearchTool/*`, `constants/prompts.ts` | Lets model discover deferred tools to reduce prompt size. | tool metadata/search query. | matching tool metadata. | None or registry lookup. | Yes. | No. | ToolRegistry search service. | Can map to LangGraph tool-selection node. |
| Agent/subagent | `src/tools/AgentTool/*`, `src/constants/prompts.ts`, `src/tasks/*` | Spawns subagents, sidechain conversations, background tasks, teams. | prompt, agent type, tools, context. | agent result/progress. | Creates sessions/tasks, may run tools. | Yes, subgraph. | Agent definitions are skill-like. | Agent service. | Forked skill execution depends on this. |
| Task tools | `src/tools/TaskCreateTool`, `TaskUpdateTool`, `TaskListTool`, `TaskGetTool`, `TaskOutputTool`, `TaskStopTool` | Create/list/update/stop task records/background work. | task params. | task state/results. | Persistent/in-memory task changes. | Yes. | No. | TaskService. | Useful for project/session workflow. |
| Todo write | `src/tools/TodoWriteTool/*` | Maintains todo/task list in conversation. | todo items. | updated todo state. | App state mutation. | Yes. | No. | TodoService. | Direct LangGraph state mutation. |
| Ask user question | `src/tools/AskUserQuestionTool/*`, permission components | Lets model request structured user confirmation/choice. | question/options. | user answer. | Blocks turn until UI/user response. | Yes. | Skill-like capability. | ConfirmationService. | Important for user confirmations. |
| Enter/Exit plan mode | `src/tools/EnterPlanModeTool`, `ExitPlanModeTool`, permission components | Switches permission mode and asks for plan approval. | plan content/permission update. | approval/denial and mode changes. | Changes permission mode/session. | Yes. | Skill-like workflow. | Permission/Plan service. | Map to planning subgraph. |
| Permission rules | `src/utils/permissions/*`, `src/hooks/useCanUseTool.tsx` | Applies allow/deny/ask rules, modes, classifiers, hooks. | tool name/input/context. | allow/deny/ask decision. | May persist rule updates. | Yes, permission gate. | No. | PermissionService. | Required for every risky tool. |
| Hook execution | `src/services/tools/toolHooks.ts`, `utils/hooks.ts`, schemas | Runs pre/post/permission/session hooks. | hook event payload. | extra messages/decision/block. | Executes configured commands/plugins. | Yes. | No. | HookService. | Hooks can inject context or block tools. |
| Input processing | `src/utils/processUserInput/*`, `src/history.ts` | Parses prompt text, slash commands, images, pasted content, at-mentions, hooks. | raw input and pasted contents. | messages, shouldQuery, allowed tools. | Stores images, records history, triggers hooks. | Yes. | No. | InputService/AttachmentService. | First graph node. |
| File attachments/at-mentions | `src/utils/attachments.ts` | Converts references into attachment messages and context. | paths, PDFs, memory/task refs, agent refs. | attachment messages. | Reads files/metadata, may discover skills. | Yes. | Skill-like capability. | AttachmentService. | Preserve for chat UX. |
| Remote file download/upload | `src/services/api/filesApi.ts`, `src/bridge/*`, `BriefTool/upload` | Downloads session attachments and uploads files in BYOC/remote flows. | file IDs/paths/OAuth token. | local files or file IDs. | Network and filesystem writes. | Maybe. | No. | RemoteFilesService. | Keep if remote attachments retained. |
| Session storage/resume | `src/utils/sessionStorage.ts`, `commands/resume`, `sessionRestore.ts` | Writes JSONL transcripts, lists logs, restores state. | messages/session id/project path. | logs/resumed messages/state. | Filesystem persistence. | Yes, persistence/resume nodes. | No. | SessionStorage. | Core project/session behavior. |
| Memory extraction | `src/services/extractMemories/*`, `src/memdir/*`, `src/services/SessionMemory/*` | Saves persistent/user/team/session memories. | conversation delta, memory files. | memory files/summary. | Reads/writes memory dirs. | Yes, memory subgraph. | Skill-like. | MemoryService. | Prompt-driven capability. |
| Compaction | `src/services/compact/*`, `src/commands/compact` | Summarizes conversation, auto/manual compaction, microcompact. | message history and options. | compacted messages/summary. | Rewrites active context, hooks. | Yes. | Skill-like workflow. | CompactionService. | Critical for long-running chats. |
| Error handling/retry | `src/services/api/withRetry.ts`, `query.ts`, `toolExecution.ts`, API error components | Handles API/tool errors, fallback, retries, UI error messages. | errors/events. | retry/fallback/visible messages. | May switch model or stop turn. | Yes. | Skill-like recovery capability. | ErrorRecoveryService. | Preserve graph error edges. |
| Export transcript | `src/commands/export/export.tsx`, `ExportDialog.tsx`, `exportRenderer.tsx` | Renders conversation and copies/saves `.txt`. | messages, tools, optional filename. | text file or clipboard content. | Writes file/clipboard. | Maybe command node. | No. | ExportService. | Direct port. |
| Context visualization | `src/commands/context/*`, `ContextVisualization.tsx`, `utils/analyzeContext.ts` | Analyzes token usage, tools, memory, skills, messages, compaction. | messages/model/tools/state. | terminal visualization/data. | Token counting API calls possible. | Maybe analysis node. | No. | ContextAnalysisService. | UI replacement optional. |
| Insights report | `src/commands/insights.ts` | Analyzes session logs and creates HTML charts/insights. | session transcripts/logs. | HTML/report/export data. | Reads/writes files, may call model. | Maybe separate graph. | Skill-like report capability. | ReportService. | This is session analytics, not user data analysis. |
| Model/provider selection | `src/utils/model/*`, `services/api/client.ts`, `main.tsx` | Resolves model/provider/settings/defaults. | env/settings/CLI. | model/provider config. | Reads settings/env/auth. | Startup node/config. | No. | ModelProviderService. | Use current Python config. |
| Cost/token tracking | `src/cost-tracker.ts`, `costHook.ts`, `utils/tokens.ts` | Tracks usage, cost, context. | API usage events. | cost summaries. | Persists session costs. | Maybe node side effect. | No. | UsageService. | Required for status/cost features. |
| Project/worktree actions | `src/tools/EnterWorktreeTool`, `ExitWorktreeTool`, `utils/worktree.ts`, commands | Creates/enters/exits git worktrees and project directories. | repo/cwd/session. | cwd/worktree state. | Git filesystem changes. | Yes for workflow. | Skill-like project action. | ProjectService. | Optional if coding assistant behavior retained. |
| LSP/IDE | `src/tools/LSPTool`, `utils/ide.ts`, hooks | Diagnostics/IDE integration. | file/project/IDE connection. | diagnostics/actions. | IDE RPC/process. | Tool node. | No. | IDEService. | Optional. |
| Voice/input/keybindings | `src/voice`, `src/hooks/useVoice*`, `keybindings`, `vim` | Voice and terminal input UX. | user input/audio/key events. | text/input state. | audio process/terminal state. | No. | No. | UI service only. | Not core LangGraph. |
| Plugin install/manage | `src/commands/plugin`, `src/utils/plugins/*` | Install/update/enable/disable plugins and marketplaces. | plugin identifiers, marketplace config. | plugin state. | Git/network/filesystem. | Maybe command workflow. | No. | PluginService. | Keep if plugin ecosystem retained. |
| Built-in plugin scaffolding | `src/plugins/builtinPlugins.ts`, `src/plugins/bundled/index.ts` | User-toggleable bundled plugin registry. | plugin definition. | enabled/disabled plugin list. | Settings reads/writes. | No. | Can provide skills. | PluginService. | No registered built-ins yet. |
| Data file parsing | `FileReadTool`, `constants/files.ts`, `mcpOutputStorage.ts` | Basic file reading and mime extension mapping. | local path or persisted MCP blob. | text/binary path/readable content. | File reads/writes. | Tool node. | No. | FileService. | No dedicated CSV/Excel/Parquet dataframe parser. |
| Chart/data visualization | `ContextVisualization.tsx`, `commands/insights.ts`, notebook read outputs | Context and session-analytics visualizations; notebook outputs can include visualizations. | token/session data/notebook file. | terminal UI/HTML report/notebook output. | HTML file maybe. | Maybe. | No. | Report/UI service. | No arbitrary dataset chart artifact generator. |
| General artifacts | scattered `artifact` mentions, SDK `artifact_urls`, exports/tool output storage | No unified artifact CRUD system. | tool/report/session output. | URLs/files. | Writes files/tool-result storage. | Maybe storage node. | No. | Artifact/OutputStorage if target needs it. | Treat target artifacts as new design unless source recovered. |

## Data Analyst Capability Finding

The user-requested data analyst capabilities were specifically checked:

| Capability | Evidence in source | Classification |
| --- | --- | --- |
| Read CSV | `.csv` appears in file/mime constants and examples; no CSV dataframe parser or profiler found. | Low-level file/tool support only. |
| Read Excel | `.xls/.xlsx` appear as binary extensions and MCP output extension mapping; no Excel parser workflow found. | Low-level file/tool support only. |
| Read Parquet | `parquet` search returned 0 source files. | Not present. |
| Dataset profiling | No dataset profile service/workflow found. | Not present. |
| Answer questions over dataset | No analyst/dataframe graph found. | Not present. |
| Generate Python analysis code | Bash/PowerShell can run commands, but no data-analysis code-generation skill found. | Generic shell capability only. |
| Safe Python execution | No dedicated Python sandbox for analyst code; shell tools have permissions. | Not present as data analyst service. |
| Build chart | Only session insights HTML charts and context visualization. | Not present for user datasets. |
| Artifact create/update/preview | No unified artifact model. | Not present. |

Migration implication: a Python/LangGraph data analyst app would require new skills/services for file ingestion, dataframe profiling, code execution, charting, and artifacts. Those cannot be described as direct ports from this audited source.

## New Architecture Classification Rules Applied

- Workflow/state/transition behavior becomes LangGraph nodes/subgraphs.
- Reusable prompt-driven capabilities become Skills.
- Low-level operations become Tools/Services.
- Display-only terminal behavior becomes UI layer.
- Prompt-driven capabilities such as compact, memory extraction, skill execution, and insights report generation must be represented as skill plus prompt template plus graph node when retained.
