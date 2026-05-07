# Reference Runtime Capability Matrix

Current audit date: 2026-05-07

This matrix describes the current Python/LangGraph runtime, not historical pre-fix status.

| Capability | Status | Evidence | Tests | Docs | Remaining work | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Core StateGraph workflow | working | `graph/builder.py` defines graph nodes and conditional edges. | `test_graph_smoke.py`, runtime audit tests | `GRAPH_ARCHITECTURE.md` | Keep nodes thin during future phases. | P1 |
| LangGraph interrupt/resume | working | `permission_gate`, `AssistantGraphRuntime.resume` | `test_permission_interrupts.py`, `test_api_frontend_contract.py` | `PERMISSIONS.md` | Frontend approval UX later. | P1 |
| CLI chat | working | `cli.py chat` uses shared runtime and one session id per loop. | observability CLI tests | README | Rich TUI remains future. | P2 |
| Headless query | working | `cli.py query` | `test_cli_headless.py` | README | More SDK event variants optional. | P2 |
| Stream JSON | working | `AssistantGraphRuntime.stream` yields UI events. | `test_cli_headless.py`, observability stream tests | README, `OBSERVABILITY.md` | Replay harness should pin event contracts. | P1 |
| API/frontend contract | partial | `api` package, frontend static tests | `test_api_frontend_contract.py`, frontend static tests | `FRONTEND.md` | Full frontend UI after runtime readiness. | frontend_phase |
| Tool registry | working | `ToolRegistry`, core tool factory | `test_tool_registry.py` | `TOOLS.md` | Add deferred ToolSearch later if needed. | P2 |
| File tools | working | `file_tools.py`, `FileService` | `test_file_tools.py`, runtime tools tests | `TOOLS.md` | MultiEdit/patch batch missing. | P1 |
| Notebook tools | working | `notebook_tools.py` | runtime tools tests | `TOOLS.md` | Rich notebook rendering optional. | P3 |
| Search tools | working | `glob`, `grep` | `test_search_tools.py` | `TOOLS.md` | Ranking/UI polish optional. | P3 |
| Shell tools | working | `bash`, `powershell`, `ShellService` | `test_shell_permissions.py` | `PERMISSIONS.md`, `TOOLS.md` | More source shell parsing optional. | P2 |
| Web tools | partial | `web_fetch` guarded; `web_search` needs provider | `test_web_tools.py` | `TOOLS.md` | Implement real search provider if required. | P2 |
| Todo tool | working | `todo_write` | runtime audit tests | `TOOLS.md` | Source task integration broader. | P2 |
| Agent tool/subgraph | partial | `agent`, `agent_graph`, synthetic `AgentService` | `test_subagent_graph.py` | `GRAPH_ARCHITECTURE.md` | Phase 5 real subagents. | P1 |
| Task tool | partial | `task_tools.py` placeholder not in core registry | limited coverage | Technical debt docs | Decide under Phase 5. | P1 |
| Permission metadata | working | `ToolPermissionMetadata`, `PermissionService` | metadata-driven permission tests | `PERMISSIONS.md` | Continue enforcing for new extension tools. | P1 |
| Typed tool effects | working | `ToolStateEffect`, controlled applier | `test_tool_state_effects_metadata.py` | `PYDANTIC_BOUNDARIES.md` | Add effect types only through tests. | P1 |
| Skills registry/loader | working | `skills/registry.py`, `loader.py` | skill loader/registry tests | `SKILLS.md` | Advanced frontmatter fields partial. | P2 |
| SkillTool and skill graph | working | `skill_tool.py`, `skill_router.py` | skill invocation and runtime audit tests | `SKILLS.md` | Inline/forked source behavior not ported. | P2 |
| Skill effects | working | `SkillEffect`, controlled memory write | skill args runtime tests | `PYDANTIC_BOUNDARIES.md`, `SKILLS.md` | Add new effect kinds only if needed. | P1 |
| Built-in skills | working | SKILL.md definitions for core skills | runtime skill tests | `SKILLS.md` | Optional source-specific skills intentionally disabled. | P2 |
| Plugin skills | working | `PluginService`, `load_plugin_contributions` | Superpowers/plugin tests | `PLUGINS.md` | Plugin tools/commands/MCP SDK partial. | P1 |
| Superpowers plugin | working | external fixture/git-source plugin path | `test_superpowers_plugin.py` | `SUPERPOWERS_PLUGIN.md` | Live GitHub smoke remains optional/manual. | P1 |
| Plugin policy contributions | working | generic `PluginPolicyContribution` and evaluator | `test_plugin_policy_contributions.py` | `PLUGINS.md` | More policy result types later. | P1 |
| Plugin install/update/remove | partial | local and git source install, timeout | plugin tests | `PLUGINS.md` | Marketplace and richer trust model. | P2 |
| Hook models/registry/service | working | `models/hooks.py`, hooks package, `HookService` | hook model/registry/service tests | `HOOKS.md` | `session_end` has no natural boundary. | P2 |
| Graph-owned hooks | working | hooks called at lifecycle points | hook graph tests | `GRAPH_ARCHITECTURE.md`, `HOOKS.md` | Executable hooks intentionally not MVP. | P1 |
| Hook applier | working | controlled HookResult application | `test_hooks_applier.py` | `HOOKS.md` | Keep immutable updates for new actions. | P1 |
| MCP config/models | working | `models/mcp.py`, `MCPService` diagnostics | MCP config/model tests | `MCP.md` | Full config layering in Phase 8. | P1 |
| MCP stdio transport | working | JSON-RPC stdio transport and fake server | MCP stdio/discovery tests | `MCP.md` | HTTP/OAuth not implemented. | P1 |
| MCP tools | working | `MCPToolAdapter`, `mcp_graph` route | MCP tool registry/runtime tests | `MCP.md`, `TOOLS.md` | More output storage/truncation refinements optional. | P2 |
| MCP resources/prompts | partial | list/read/get supported | MCP resources/prompts tests | `MCP.md` | Prompt-to-skill registration disabled by default. | P2 |
| MCP diagnostics | working | `/mcp`, `/doctor` invalid config visibility | MCP command tests | `MCP.md`, `COMMANDS.md` | More CLI subcommands optional. | P2 |
| Slash command registry | working | `commands/builtin.py` | command registry/router tests | `COMMANDS.md` | Rich source command surface not complete. | P2 |
| Unsupported optional commands | honest_partial | `/rewind`, `/branch`, `/rename`, `/tag`, `/context` placeholders | command tests | `COMMANDS.md` | Implement only if product needs them. | P2 |
| Sessions storage | working | strict id validation and path confinement | session storage tests | `SESSIONS.md` | Session browser/rename/tag later. | P1 |
| Resume/export | working | `SessionService`, `ExportService` | resume/export tests | `SESSIONS.md`, `COMMANDS.md` | Source picker UI later. | P2 |
| Memory | working | `MemoryService`, `/memory`, remember skill | memory tests | `SKILLS.md`, `SESSIONS.md` | Automatic extraction/relevance partial. | P2 |
| Compaction | working | compaction graph/service | compaction tests | `GRAPH_ARCHITECTURE.md` | Source microcompact variants partial. | P2 |
| Observability/Langfuse | working_optional | `ObservabilityService`, trace-turn scoping | observability tests | `OBSERVABILITY.md` | Real-key smoke manual only. | P1 |
| Runtime events | working | `ui_events` reducers and persistence | runtime audit/event tests | `GRAPH_ARCHITECTURE.md` | Eval/replay harness should lock contracts. | P1 |
| Config/env precedence | working | `AppConfig.from_env`, `layered_get` | env/langfuse config tests | README, `.env.example` | Full user/project config layering later. | P1 |
| Provider abstraction | partial | fake/openai/anthropic/ollama/openai-compatible config | provider binding tests | README | Provider-specific auth/cost/retry polishing. | P2 |
| Security hardening | working | Batch 1 and Batch 2 fixes | security-focused regression tests | audit docs, `PERMISSIONS.md` | Keep external content untrusted. | P0/P1 |
| Context providers/attachments | missing | No first-class attachment model | none specific | roadmap only | Phase 6. | P1 |
| Eval/replay harness | missing | No replay runner | none specific | roadmap only | Phase 7. | P1 |
| Frontend readiness | partial | Static React shell and API contract | frontend static tests | `FRONTEND.md` | Build real UI after Phase 8. | frontend_phase |

