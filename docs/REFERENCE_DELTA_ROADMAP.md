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

### Phase 5: Real Subagents

- Why it matters: replaces the synthetic child run with isolated child graph execution.
- Source basis: `src/tools/AgentTool`, `src/tasks`, `src/coordinator`, `Task*`, `Team*`, `SendMessageTool`, `TaskStopTool`.
- Current status: working MVP with different architecture.
- Evidence: `models/subagents.py`, `agent_graph`, child-run persistence, subagent runtime/permission/observability tests.
- Remaining work: nested approval resume, parallel/background task lifecycle, stop/list/show task commands, richer exports.

### Phase 6: Context Providers and Attachments

- Why it matters: source has attachments, image refs, context suggestions, context budget, tool result storage, and context visualization. This is the biggest gap before a good frontend.
- Source basis: `src/utils/attachments.ts`, `src/components/ContextVisualization.tsx`, `src/utils/tokens.ts`, `src/utils/toolResultStorage.ts`, prompt input attachment handling.
- Current status: working MVP with documented image/PDF limitations.
- Target architecture: typed context-provider services feeding `context_builder`; untrusted external context markers; attachment models for files/images/PDFs/notebooks/MCP resources; budget accounting.
- LangGraph nodes/subgraphs: `normalize_input` extracts refs, `resolve_context` resolves/budgets, `context_builder` consumes rendered fragments.
- Pydantic models: `ContextReference`, `AttachmentRef`, `AttachmentContent`, `ContextFragment`, `ContextBudgetReport`, `ResolvedContextItem`.
- Services: `ContextProviderService`, `ContextBudgetService`.
- Tests: file refs, Windows paths, large attachments, binary/image placeholders, MCP resource as context, prompt injection markers, budget truncation, stream events, subagent inheritance.
- Risks: prompt injection, secret/path leaks, huge payloads, frontend/API mismatch; core guardrails are in place.
- Dependencies: current web/MCP/plugin trust boundaries.
- Priority: P1.

### Phase 7: Eval and Replay Harness

- Why it matters: runtime now has graph edges, permissions, hooks, MCP, plugins, skills, memory, and observability. Unit tests are strong, but real transcript regressions need replay.
- Source basis: source has rich SDK/stream events and transcript/session storage; replay harness is an extension needed for this reference runtime.
- Current status: working MVP.
- Target architecture: deterministic scenario runner over checked-in fixtures, fake provider, RuntimeEvents, permission decisions, and final graph state.
- LangGraph nodes/subgraphs: no new workflow owner; harness invokes existing `AssistantGraphRuntime`.
- Pydantic models: `EvalScenario`, `EvalStep`, `EvalExpectations`, `ExpectedEvent`, `ExpectedToolCall`, `ExpectedSkillInvocation`, `ExpectedPermissionRequest`, `ExpectedMCPCall`, `ExpectedSubagentRun`, `ExpectedContextFragment`, `ExpectedFinalResponse`, `EvalRunResult`, `EvalReport`.
- Services: `EvalService`, `EvalRunner`, loader, assertion engine, reporter.
- Tests: basic chat, file context, write rejection, edit exact-once/ambiguous, Superpowers activation, MCP echo, hook block, readonly subagent, URL disabled, Langfuse disabled.
- Risks: future real-provider evals need stricter fixture controls; prose assertions should remain tolerant.
- Dependencies: stable event contracts and session storage.
- Priority: P1.

### Phase 8: Config Layering and Plugin SDK Hardening

- Why it matters: source has broader settings/auth/model/plugin/MCP behavior, and frontend needs a stable runtime contract instead of ad hoc UI logic.
- Source basis: source settings, auth, model, plugin, MCP, feature gate, and update commands.
- Current status: working MVP.
- Target architecture: explicit config layers: CLI args > process env > project config > user config > `.env` > defaults, with typed diagnostics and redaction. Plugin SDK declares skills, hooks, policies, commands, tools, MCP, context providers, bootstrap context, and trust requirements.
- LangGraph nodes/subgraphs: keep config loading at bootstrap/load-registry boundaries.
- Pydantic models: `ConfigSource`, `ConfigValueOrigin`, `ConfigDiagnostic`, `EffectiveConfigReport`, `PluginCommandContribution`, `PluginToolContribution`, `PluginMCPContribution`, `PluginContextProviderContribution`, `PluginTrustPolicy`.
- Services: config loader/explain renderer, plugin SDK validator, declarative plugin tool/context adapters.
- Tests: precedence, redaction, invalid config diagnostics, plugin contribution validation, plugin command/tool/MCP/context security, example-plugin eval scenarios.
- Risks: future trusted executable plugin adapters need a separate trust and sandbox design.
- Dependencies: completed plugin/hook/MCP foundations.
- Priority: P1.

## Remaining MVP Before Frontend

No backend/runtime phase is currently blocking frontend start. Remaining items are focused cleanup or future source deltas.

## Roadmap Adjustments From Re-Sync

1. Phase 5 now covers the local real subagent baseline.
   Remaining source task lifecycle deltas are nested approval resume, stop/list/show commands, parallel/background teams, and richer child export/replay.

2. Keep Phase 6 as context providers/attachments, but treat it as runtime, not frontend polish.
   Frontend attachment UI should follow typed runtime support, not precede it.

3. Phase 7 is now the regression harness before frontend.
   Use checked-in scenarios to protect later plugin SDK, config, and UI work.

4. Phase 8 is now complete enough for frontend to consume config diagnostics and plugin contribution metadata.

5. Move provider-specific cost accounting into a small frontend-readiness cleanup or future usage phase.
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
- Current status: local sequential child graph baseline exists; background/team/remote task lifecycle is not implemented.
- Reason: remote/background coordination belongs after the local child-run lifecycle is stable.

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
