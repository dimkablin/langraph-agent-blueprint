# Reference Runtime Capability Matrix

Current audit date: 2026-05-07
Last readiness update: 2026-05-13

This matrix describes the current Python/LangGraph runtime, not historical pre-fix status.

| Capability | Status | Evidence | Tests | Docs | Remaining work | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Core StateGraph workflow | working | `graph/builder.py` defines graph nodes and conditional edges. | `test_graph_smoke.py`, runtime audit tests | `GRAPH_ARCHITECTURE.md` | Keep nodes thin during future phases. | P1 |
| LangGraph interrupt/resume | working | `permission_gate`, `AssistantGraphRuntime.resume` | `test_permission_interrupts.py`, `test_api_frontend_contract.py` | `PERMISSIONS.md` | Frontend approval UX later. | P1 |
| CLI chat | working | `cli.py chat` uses shared runtime and one session id per loop. | observability CLI tests | README | Rich TUI remains future. | P2 |
| Headless query | working | `cli.py query` | `test_cli_headless.py` | README | More SDK event variants optional. | P2 |
| Stream JSON | working | `AssistantGraphRuntime.stream` yields UI events. | `test_cli_headless.py`, observability stream tests | README, `OBSERVABILITY.md` | Replay harness should pin event contracts. | P1 |
| API/frontend contract | working_mvp | `api` package exposes chat, SSE, approval, sessions, context, child runs, export, registry/status/config/MCP/plugin/hook/observability, and workspace routes consumed by the frontend. | `test_api_frontend_contract.py`, frontend static/unit tests | `FRONTEND.md`, `API_FRONTEND_CONTRACT.md` | Direct todo/memory/command endpoints, upload/download endpoints, and richer command-specific APIs are post-MVP. | P1 |
| Tool registry | working | `ToolRegistry`, core tool factory | `test_tool_registry.py` | `TOOLS.md` | Add deferred ToolSearch later if needed. | P2 |
| File tools | working | `file_tools.py`, `FileService` | `test_file_tools.py`, runtime tools tests | `TOOLS.md` | MultiEdit/patch batch missing. | P1 |
| Notebook tools | working | `notebook_tools.py` | runtime tools tests | `TOOLS.md` | Rich notebook rendering optional. | P3 |
| Search tools | working | `glob`, `grep` | `test_search_tools.py` | `TOOLS.md` | Ranking/UI polish optional. | P3 |
| Shell tools | working | `bash`, `powershell`, `ShellService` | `test_shell_permissions.py` | `PERMISSIONS.md`, `TOOLS.md` | More source shell parsing optional. | P2 |
| Web tools | partial | `web_fetch` guarded; `web_search` needs provider | `test_web_tools.py` | `TOOLS.md` | Implement real search provider if required. | P2 |
| Todo tool | working | `todo_write` | runtime audit tests | `TOOLS.md` | Source task integration broader. | P2 |
| Agent tool/subgraph | working_mvp | `agent`, `agent_graph`, `models/subagents.py`, child-run storage | `test_subagent_graph.py`, `test_subagent_graph_runtime.py`, `test_subagent_permissions.py`, `test_subagent_observability.py` | `SUBAGENTS.md`, `GRAPH_ARCHITECTURE.md` | Nested approval resume, parallel/background task lifecycle. | P1 |
| Task tool | partial | `task_tools.py` placeholder not in core registry | limited coverage | Technical debt docs | Stop/list/show and background task lifecycle after local subagent baseline. | P1 |
| Permission metadata | working | `ToolPermissionMetadata`, `PermissionService` | metadata-driven permission tests | `PERMISSIONS.md` | Continue enforcing for new extension tools. | P1 |
| Typed tool effects | working | `ToolStateEffect`, controlled applier | `test_tool_state_effects_metadata.py` | `PYDANTIC_BOUNDARIES.md` | Add effect types only through tests. | P1 |
| Skills registry/loader | working | `skills/registry.py`, `loader.py` | skill loader/registry tests | `SKILLS.md` | Advanced frontmatter fields partial. | P2 |
| SkillTool and skill graph | working | `skill_tool.py`, `skill_router.py` | skill invocation and runtime audit tests | `SKILLS.md` | Inline/forked source behavior not ported. | P2 |
| Skill effects | working | `SkillEffect`, controlled memory write | skill args runtime tests | `PYDANTIC_BOUNDARIES.md`, `SKILLS.md` | Add new effect kinds only if needed. | P1 |
| Built-in skills | working | SKILL.md definitions for core skills | runtime skill tests | `SKILLS.md` | Optional source-specific skills intentionally disabled. | P2 |
| Plugin skills | working | `PluginService`, `load_plugin_contributions` | Superpowers/plugin tests | `PLUGINS.md`, `PLUGIN_SDK.md` | Advanced skill frontmatter remains partial. | P1 |
| Plugin commands/tools/context/MCP | working_mvp | `PluginCommandContribution`, `PluginToolContribution`, `PluginContextProviderContribution`, plugin MCP merge | Phase 8 plugin SDK tests and eval scenarios | `PLUGIN_SDK.md`, `PLUGINS.md` | Trusted executable plugin adapters and marketplace are not MVP. | P1 |
| Superpowers plugin | working | external fixture/git-source plugin path | `test_superpowers_plugin.py` | `SUPERPOWERS_PLUGIN.md` | Live GitHub smoke remains optional/manual. | P1 |
| Plugin policy contributions | working | generic `PluginPolicyContribution` and evaluator | `test_plugin_policy_contributions.py` | `PLUGINS.md` | More policy result types later. | P1 |
| Plugin install/update/remove | partial | local and git source install, timeout | plugin tests | `PLUGINS.md` | Marketplace and richer trust model. | P2 |
| Hook models/registry/service | working | `models/hooks.py`, hooks package, `HookService` | hook model/registry/service tests | `HOOKS.md` | `session_end` has no natural boundary. | P2 |
| Graph-owned hooks | working | hooks called at lifecycle points | hook graph tests | `GRAPH_ARCHITECTURE.md`, `HOOKS.md` | Executable hooks intentionally not MVP. | P1 |
| Hook applier | working | controlled HookResult application | `test_hooks_applier.py` | `HOOKS.md` | Keep immutable updates for new actions. | P1 |
| MCP config/models | working | `models/mcp.py`, `MCPService` diagnostics, TOML/env/plugin config sources | MCP config/model tests, plugin MCP tests | `MCP.md`, `CONFIG.md` | HTTP/OAuth not implemented. | P1 |
| MCP stdio transport | working | JSON-RPC stdio transport and fake server | MCP stdio/discovery tests | `MCP.md` | HTTP/OAuth not implemented. | P1 |
| MCP tools | working | `MCPToolAdapter`, `mcp_graph` route | MCP tool registry/runtime tests | `MCP.md`, `TOOLS.md` | More output storage/truncation refinements optional. | P2 |
| MCP resources/prompts | partial | list/read/get supported | MCP resources/prompts tests | `MCP.md` | Prompt-to-skill registration disabled by default. | P2 |
| MCP diagnostics | working | `/mcp`, `/doctor` invalid config visibility | MCP command tests | `MCP.md`, `COMMANDS.md` | More CLI subcommands optional. | P2 |
| Slash command registry | working | `commands/builtin.py` | command registry/router tests | `COMMANDS.md` | Rich source command surface not complete. | P2 |
| Unsupported optional commands | honest_partial | `/rewind`, `/branch`, `/rename`, `/tag` placeholders | command tests | `COMMANDS.md` | Implement only if product needs them. | P2 |
| Sessions storage | working | strict id validation and path confinement | session storage tests | `SESSIONS.md` | Session browser/rename/tag later. | P1 |
| Resume/export | working | `SessionService`, `ExportService` | resume/export tests | `SESSIONS.md`, `COMMANDS.md` | Source picker UI later. | P2 |
| Memory | working | `MemoryService`, `/memory`, remember skill | memory tests | `SKILLS.md`, `SESSIONS.md` | Automatic extraction/relevance partial. | P2 |
| Compaction | working | compaction graph/service | compaction tests | `GRAPH_ARCHITECTURE.md` | Source microcompact variants partial. | P2 |
| Observability/Langfuse | working_optional | `ObservabilityService`, trace-turn scoping | observability tests | `OBSERVABILITY.md` | Real-key smoke manual only. | P1 |
| Runtime events | working | `ui_events` reducers and persistence | runtime audit/event tests | `GRAPH_ARCHITECTURE.md` | Eval/replay harness should lock contracts. | P1 |
| Config layering/explain | working_mvp | `AppConfig.load_with_report`, `ConfigSource`, `EffectiveConfigReport`, `lg-agent config ...` | config layering/commands tests | README, `.env.example`, `CONFIG.md` | More provider-specific auth validation optional. | P1 |
| Provider abstraction | partial | fake/openai/anthropic/ollama/openai-compatible config | provider binding tests | README | Provider-specific auth/cost/retry polishing. | P2 |
| Security hardening | working | Batch 1 and Batch 2 fixes | security-focused regression tests | audit docs, `PERMISSIONS.md` | Keep external content untrusted. | P0/P1 |
| Context providers/attachments | working_mvp | `models/context.py`, `context/providers.py`, `resolve_context` graph node, `/context` | context model/provider/graph/security/subagent/observability tests | `CONTEXT_ATTACHMENTS.md` | Image/PDF extraction is metadata-only; frontend attachment UX remains future. | P1 |
| Eval/replay harness | working_mvp | `models/evals.py`, `evals/loader.py`, `evals/runner.py`, `evals/assertions.py`, `evals/reporter.py`, `lg-agent eval ...` | `test_eval_models.py`, `test_eval_loader.py`, `test_eval_assertions.py`, `test_eval_runner.py`, `test_eval_cli.py`, `test_eval_scenarios.py` | `EVAL_REPLAY.md`, README | Add optional Langfuse scoring and richer replay diffs later. | P1 |
| Frontend readiness | working_mvp | TypeScript React/Vite frontend with chat, SSE timeline, permission panel, sessions, context window, settings center, runtime/sidebar panels, workspace controls, and local UI preferences. | `npm.cmd --prefix frontend run test:static`, `npm.cmd --prefix frontend run test`, `npm.cmd --prefix frontend run build` | `FRONTEND.md`, `FRONTEND_IMPLEMENTATION_PLAN.md` | Playwright/browser smoke, upload/download UX, richer subagent transcript view, plugin management UI, eval dashboard. | P1 |
