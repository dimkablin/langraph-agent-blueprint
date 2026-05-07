# Source Re-Sync Audit

Current audit date: 2026-05-07

This is an audit-only document. No production code or tests were changed as part of this source re-sync pass.

## Baseline

Commands run in `C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint`:

```powershell
git status --short
python -m pytest -q
npm.cmd --prefix frontend run test:static
```

Result:

- `git status --short`: clean output; only external Git warning about `C:\Users\dimka/.config/git/ignore` permission.
- `python -m pytest -q`: passed.
- `npm.cmd --prefix frontend run test:static`: passed.

Baseline status: green.

## Source Paths Checked

Checked source candidates:

```text
C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project
C:\Users\dimka\Documents\PROJECTS\claude-code-like-project
```

Both paths exist.

Comparison:

- Both contain `1905` files by `rg --files`.
- Both have the same top-level source structure.
- Both README files have the same SHA256 hash: `2B808F0CFAEA9EF8760B7BDC88802D501401F0CF51F1051AF43A5727AA666615`.
- Both relative file-list hashes match: `41E63844199B3A7DD4EB466293DB912677E5ABB8A5DC4D9790AD451C5ABC2BA8`.
- Neither candidate is a Git worktree.

Selected reference source:

```text
C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project
```

Reason: it is the primary path named in the current task and it is equivalent to the second candidate based on file count and content hashes.

Do not use the old non-existent path `claude-like-project`.

## Provenance Boundary

The reference README describes the source as a reconstructed/leaked Claude Code-like source tree. This audit does not copy proprietary prompts or implementation text. It compares capability boundaries, workflows, file organization, architecture, and behavior categories.

## Source Structure Confirmed

Confirmed top-level `src` areas in the reference source:

```text
assistant
bootstrap
bridge
buddy
cli
commands
components
constants
context
coordinator
entrypoints
hooks
ink
keybindings
memdir
migrations
moreright
native-ts
outputStyles
plugins
query
remote
schemas
screens
server
services
skills
state
tasks
tools
types
upstreamproxy
utils
vim
voice
```

The source is a TypeScript/Bun React+Ink terminal coding assistant. It is not a browser-first data analyst app.

## Source Capabilities Confirmed

Confirmed source capability families:

- Interactive terminal UI and headless query entrypoints.
- SDK and structured IO schemas.
- Server/direct-connect/remote session surfaces.
- Model query loop, streaming, token budget, stop hooks, and tool orchestration.
- File, shell, search, notebook, web, todo, MCP, skill, agent, task, team, worktree, and LSP tools.
- Large slash command surface, including session, model, auth, config, update, MCP, plugin, hooks, memory, permissions, review, task, UI, and remote commands.
- Bundled skills such as `verify`, `debug`, `remember`, `simplify`, `skillify`, `stuck`, `batch`, and several optional or source-specific skills.
- Executable hook system with many event names, including tool, prompt, session, permission, file, cwd, worktree, and subagent hooks.
- MCP client with resources, tools, OAuth/auth surfaces, official registry support, and VS Code/remote integration points.
- Plugin installation and bundled plugin surfaces.
- Task, team, remote-agent, background, coordinator, and swarm-like subagent concepts.
- Memory directories, memory extraction, session memory, and team memory.
- Compaction variants, including auto, micro, session-memory, and cleanup flows.
- Attachments, image handling, context visualization, context suggestions, and context-window accounting.
- React+Ink terminal UX: permission dialogs, resume picker, keybindings, voice, vim mode, transcript rendering, and rich tool result displays.

## Previously Known Findings Reconfirmed

Old migration/audit docs were broadly accurate on these points:

- The source is Claude Code-like terminal/runtime code, not a data analyst web app.
- Python runtime is a LangGraph redesign, not a line-by-line port.
- Core command, tool, skill, permission, session, memory, compaction, and stream-json behavior has been ported or redesigned.
- Source has a much wider TUI and command surface than the current Python CLI.
- Source has real subagent/task/team/background features that are still only partial in the Python runtime.
- Source has a richer context/attachment layer than the current runtime.
- Source has broader config/auth/model/update and provider-specific behavior than the current runtime.

## Newly Reconfirmed or Underweighted Source Areas

The source recheck makes these areas more important for the roadmap:

1. Real subagents are bigger than a single `AgentTool`.
   Source includes `AgentTool`, task tools, team tools, coordinator mode, worker notifications, and remote-agent task lifecycle. Current Python has an `agent` tool and `agent_graph`, but the service is still synthetic.

2. Context providers and attachments are a major missing runtime layer.
   Source has attachment handling, image refs, context suggestions, context visualization, context-window accounting, and tool result storage that treats attachments specially. Current Python primarily relies on file/search tools plus context builder.

3. Tool discovery and deferred tool loading are source capabilities.
   Source has `ToolSearchTool` and deferred tool search utilities. Current Python lists tools and binds all registered tools, but does not have a model-callable deferred tool discovery flow.

4. Source hook system is executable and broader.
   Current hooks are safer and graph-owned, but data-only. Source supports executable hooks and many more hook events. This is intentionally not copied for MVP until trust policy is mature.

5. MCP source support is broader than Phase 2.
   Current Python supports stdio client operations. Source also has MCP auth/OAuth, registry, connector, VS Code, and richer resource output behavior.

6. Source terminal UX is much richer than current CLI.
   Frontend should not start until runtime readiness, but the source has concrete UX targets for permission, resume, context, tool rendering, and keybindings.

## Current Capabilities That Are Extensions, Not Direct Source Ports

These are our architecture additions or hardening choices rather than direct ports:

- Pydantic boundary contracts.
- Metadata-driven tool semantics.
- Strict session/thread id validation and path confinement.
- Immutable/minimal `ToolExecutionContext`.
- Exact-once `edit_file`.
- `web_fetch` scheme/private-host/size guardrails.
- Superpowers external plugin integration.
- Graph-owned typed hooks architecture.
- MCP stdio client implementation details in Python.
- Langfuse observability and trace-scoped runtime events.
- Generic plugin policy contributions.
- `SkillEffect` layer for durable skill side effects.
- Conservative external/plugin/MCP permission defaults.

## Current Architecture Stronger Than Source

The Python runtime is stricter than the reference source in these areas:

- LangGraph owns workflow edges and interrupt/resume.
- Tool routing is based on `ToolRuntimeMetadata`, not tool-name prefixes.
- Permission behavior is metadata-driven.
- Tool state effects are typed and applied by the runtime.
- External plugin hooks are declarative/data-only by default.
- MCP tools are conservative by default and route through graph/permissions.
- Runtime IDs are validated before filesystem use.
- Langfuse paths and secrets are redacted by default.

## Missing or Partial Source Deltas

Highest-value remaining deltas:

1. Real subagents and task lifecycle.
   Current `AgentService.run_child()` returns a synthetic completed child run. Source has worker prompts, task lifecycle, stop/update/list tools, team coordination, and remote polling.

2. Context providers and attachments.
   Current runtime lacks a first-class attachment/context-provider model for at-mentions, pasted images, PDFs, notebooks as attachments, git diff context, IDE context, and context visualization.

3. Eval and replay harness.
   Current tests are strong, but there is no dedicated replay/eval harness for real transcript/tool/permission regressions.

4. Config layering and provider/auth commands.
   Current config/env precedence is hardened, but source has broader settings, auth, model, feature gate, and update flows.

5. Plugin SDK completeness.
   Current plugins support skills, hooks, policies, git/local install, and Superpowers. Source plugin surface is broader: commands, MCP contributions, bundled plugins, marketplace/registry concepts, and stronger diagnostics.

6. Tool surface gaps.
   Missing or partial source tools include `MultiEdit`, `AskUserQuestionTool`, worktree tools, `ToolSearchTool`, real task/team tools, LSP/IDE tools, sleep/REPL/remote trigger/synthetic output, and MCP auth tool.

7. Rich terminal/frontend UX.
   Current frontend is a graph-facing shell with static tests. Source has React+Ink permission dialogs, resume picker, context visualization, tool result rendering, keybindings, voice, vim mode, and many local JSX commands.

## Intentionally Not MVP

These source areas should remain out of MVP unless goals change:

- MCP server mode.
- IDE/LSP integration.
- Background/remote task management.
- Voice input.
- Vim mode and full keybinding editor.
- Remote bridge/teleport/native host/mobile/desktop surfaces.
- Release/update/auth polish tied to a production distribution.
- Source telemetry/analytics systems not relevant to this reference runtime.
- Data analyst artifacts/dataset workflow, because they are not source capabilities.

## Future Frontend Items

Frontend can eventually learn from source UI behavior, but should wait until runtime readiness:

- Permission approval/rejection UI.
- Resume/session picker.
- Rich tool result rendering and diffs.
- Context visualization and context budget.
- Tool/skill/plugin/MCP registry views.
- Keybinding help if a full terminal UI is desired.
- Attachments/image paste display once the runtime has attachment models.

## Roadmap Impact

The proposed order remains valid, with small emphasis changes:

1. Phase 5: real subagents.
   This should include task lifecycle and child-run persistence, not only a stronger `AgentTool`.

2. Phase 6: context providers and attachments.
   This should cover file refs, pasted/attached content, external untrusted resources, context budget accounting, and a context-provider registry.

3. Phase 7: eval and replay harness.
   Needed before widening subagent/plugin/MCP behavior further.

4. Phase 8: config layering and plugin SDK hardening.
   Should include provider/model/auth commands, plugin contribution diagnostics, and safe optional executable-hook design if ever desired.

5. Frontend after runtime readiness.
   Build a real operational UI only after subagents, attachments, eval/replay, and config/plugin SDK boundaries are stable.

## Docs Consistency Notes

Current docs mostly distinguish historical audit rows from current status. Stale current-sounding references remain mostly around:

- Old migration context in README near current product narrative.
- Historical MCP and hooks runtime audit files that document pre-fix state, though later sections usually clarify that phases replaced the old state.
- Optional commands are correctly listed as unsupported placeholders in current command docs.

No docs were rewritten in this pass except new audit outputs.

