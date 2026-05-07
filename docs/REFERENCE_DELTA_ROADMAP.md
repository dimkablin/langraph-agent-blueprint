# Reference Delta Roadmap

Current audit date: 2026-05-07

This roadmap is based on the source re-sync against:

```text
C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project
```

## Completed

### LangGraph Runtime Core

- Why it matters: establishes graph-owned workflow, routing, interrupt/resume, persistence, and stream events.
- Source basis: source query/tool loop and permission flow.
- Current status: working with different architecture.
- Target architecture: already graph-owned.
- Evidence: `graph/builder.py`, runtime tests.

### Metadata-Driven Tools and Permissions

- Why it matters: avoids name-based safety behavior and makes plugin/MCP tools safer.
- Source basis: source permission/tool metadata behavior, redesigned stricter.
- Current status: working extension.
- Evidence: tool metadata tests, permission tests.

### Skills Runtime

- Why it matters: source uses bundled skills and SkillTool.
- Source basis: `src/skills/bundled`, `src/tools/SkillTool`.
- Current status: working with different architecture.
- Evidence: skill loader/invocation/runtime tests.

### Superpowers External Plugin

- Why it matters: validates plugin skills, bootstrap, and policy activation.
- Source basis: not source; extension.
- Current status: working extension.
- Evidence: Superpowers tests.

### Hooks Runtime

- Why it matters: extension point for plugins, policy, observability, skills, tools, MCP, and frontend.
- Source basis: source hooks, redesigned safer.
- Current status: working with different architecture.
- Evidence: hook model/service/graph/security tests.

### MCP Client Runtime

- Why it matters: source has MCP tools/resources/auth surfaces.
- Source basis: source MCP client areas.
- Current status: stdio tools/resources/prompts working; HTTP/OAuth not MVP.
- Evidence: fake stdio MCP tests.

### Langfuse Observability

- Why it matters: runtime complexity now needs traceability.
- Source basis: not source; extension.
- Current status: working optional layer.
- Evidence: observability tests, trace scoping tests.

### Security Hardening Batches 1 and 2

- Why it matters: closed current P0/P1 runtime extension risks.
- Current status: complete.
- Evidence: commits `285092c` and `f42a1aa`.

## Remaining MVP Before Frontend

### Phase 5: Real Subagents

- Why it matters: source has much more than a synthetic child run: worker prompts, task notifications, stop/update/list tools, team coordination, and remote-task concepts.
- Source basis: `src/tools/AgentTool`, `src/tasks`, `src/coordinator`, `Task*`, `Team*`, `SendMessageTool`, `TaskStopTool`.
- Current status: partial. `agent` routes through `agent_graph`, but `AgentService.run_child()` returns a synthetic completed result.
- Target architecture: LangGraph subagent graph with isolated child state, tool-scope restrictions, child event persistence, parent merge rules, stop/resume support, and typed child-run models.
- LangGraph nodes/subgraphs: expand `agent_graph`; add child-run lifecycle nodes; preserve permission interrupts.
- Pydantic models: `SubagentConfig`, `SubagentRun`, `SubagentResult`, `SubagentEvent`, `SubagentToolScope`, possibly `TaskRecord`.
- Services: split child-run orchestration from task persistence; keep graph as workflow owner.
- Tests: real child graph invocation, tool-scope narrowing, child permission interrupt, child event persistence, parent merge, rejection/stop, stream-json, Langfuse trace nesting.
- Risks: hidden workflow loops outside graph, broad tool scopes, event duplication.
- Dependencies: existing permission/session/event/observability foundations.
- Priority: P1.

### Phase 6: Context Providers and Attachments

- Why it matters: source has attachments, image refs, context suggestions, context budget, tool result storage, and context visualization. This is the biggest gap before a good frontend.
- Source basis: `src/utils/attachments.ts`, `src/components/ContextVisualization.tsx`, `src/utils/tokens.ts`, `src/utils/toolResultStorage.ts`, prompt input attachment handling.
- Current status: missing/partial. File tools exist, but there is no first-class attachment/context-provider runtime.
- Target architecture: typed context-provider registry feeding `context_builder`; untrusted external context markers; attachment models for files/images/PDFs/notebooks/MCP resources; budget accounting.
- LangGraph nodes/subgraphs: `context_provider_load`, `attachment_ingest`, `context_budget`, optional `context_resource_read`.
- Pydantic models: `ContextProviderContribution`, `AttachmentRef`, `AttachmentContent`, `ContextFragment`, `ContextBudgetReport`.
- Services: `ContextProviderService`, `AttachmentService`, `TokenBudgetService`.
- Tests: file refs, Windows paths, large attachments, binary/image summaries, MCP resource as context, prompt injection markers, budget truncation, stream events.
- Risks: prompt injection, secret/path leaks, huge payloads, frontend/API mismatch.
- Dependencies: current web/MCP/plugin trust boundaries.
- Priority: P1.

### Phase 7: Eval and Replay Harness

- Why it matters: runtime now has graph edges, permissions, hooks, MCP, plugins, skills, memory, and observability. Unit tests are strong, but real transcript regressions need replay.
- Source basis: source has rich SDK/stream events and transcript/session storage; replay harness is an extension needed for this reference runtime.
- Current status: missing.
- Target architecture: deterministic replay runner over saved RuntimeEvents, tool fixtures, provider fixtures, and permission decisions.
- LangGraph nodes/subgraphs: no new workflow owner; harness invokes existing runtime.
- Pydantic models: `ReplayScenario`, `ReplayStep`, `ReplayExpectation`, `EvalResult`, `ToolFixture`.
- Services: `ReplayService`, `EvalService`, fixture provider.
- Tests: replay of permission approval, Superpowers activation, MCP tool call, hook block, compaction, Langfuse disabled mode.
- Risks: weak mocks that hide bugs, brittle text assertions, accidental live network.
- Dependencies: stable event contracts and session storage.
- Priority: P1.

### Phase 8: Config Layering and Plugin SDK Hardening

- Why it matters: source has broader settings/auth/model/plugin/MCP behavior. Current config is env plus `.env`, with hardened precedence, but full layering is not done.
- Source basis: source settings, auth, model, plugin, MCP, feature gate, and update commands.
- Current status: partial.
- Target architecture: explicit config layers: CLI args > process env > project config > user config > `.env` > defaults, with typed diagnostics and redaction. Plugin SDK should declare skills, hooks, policies, commands, tools, MCP, context providers, and trust requirements.
- LangGraph nodes/subgraphs: keep config loading at bootstrap/load-registry boundaries.
- Pydantic models: `ConfigSource`, `ConfigDiagnostic`, `PluginCommandContribution`, `PluginToolContribution`, `PluginMCPContribution`, `PluginTrustPolicy`.
- Services: config loader, plugin SDK validator, diagnostics renderer.
- Tests: precedence, redaction, invalid config diagnostics, plugin contribution validation, network disabled, git timeout, Windows path behavior.
- Risks: leaking secrets, executing plugin code too early, dependency construction side effects.
- Dependencies: completed plugin/hook/MCP foundations.
- Priority: P1.

## Roadmap Adjustments From Re-Sync

1. Keep Phase 5 as real subagents, but include task lifecycle in scope.
   A minimal real subagent should not stop at spawning a model call. It should define child run identity, events, tool scopes, persistence, and parent merge rules.

2. Keep Phase 6 as context providers/attachments, but treat it as runtime, not frontend polish.
   Frontend attachment UI should follow typed runtime support, not precede it.

3. Keep Phase 7 before frontend.
   Replay/eval will make later UI and plugin SDK work safer.

4. Keep Phase 8 before frontend.
   Config layering and plugin SDK hardening are needed before exposing plugin/MCP/context providers in UI.

5. Move provider-specific cost accounting into Phase 8 or a small pre-frontend cleanup.
   `/cost` exists, but source has richer usage behavior and the frontend will need reliable numbers.

## Future / Non-MVP

### MCP Server Mode

- Source basis: `src/entrypoints/mcp.ts`.
- Current status: not implemented.
- Reason: user explicitly excluded MCP server mode from current runtime phases.

### IDE/LSP Integration

- Source basis: `LSPTool`, IDE commands, VS Code MCP bridge.
- Current status: not implemented.
- Reason: complex external integration and not needed for CLI/runtime MVP.

### Background Tasks, Teams, Remote Sessions

- Source basis: task/team/remote tools and remote polling.
- Current status: not implemented, except limited synthetic `agent`.
- Reason: real local subagents should land first.

### Full React/Ink TUI Equivalence

- Source basis: `components`, `screens`, `ink`, keybindings, vim, voice.
- Current status: current frontend is only a static shell/API contract.
- Reason: defer until runtime readiness.

### Release/Update/Auth Polish

- Source basis: update, login/logout, OAuth, upgrade commands.
- Current status: partial env/provider config.
- Reason: reference runtime should prioritize architecture, not product distribution.

### Source Telemetry Systems

- Source basis: analytics and telemetry utilities.
- Current status: intentionally not ported.
- Reason: Langfuse observability is the appropriate extension for this project; do not copy product telemetry.

### Data Analyst Artifacts and Dataset Workflows

- Source basis: absent as first-class source capability.
- Current status: intentionally not ported.
- Reason: not a direct source delta. Treat as a separate product extension if needed.

## Docs Cleanup Later

Do not block runtime phases on docs cleanup, but before frontend:

- Move current README migration/source-audit paragraphs into a historical section.
- Mark old `MCP_RUNTIME_AUDIT.md` and `HOOKS_RUNTIME_AUDIT.md` pre-phase observations as historical at the top.
- Keep `CAPABILITY_STATUS_MATRIX.md` as current acceptance source, or replace with `REFERENCE_RUNTIME_CAPABILITY_MATRIX.md`.

