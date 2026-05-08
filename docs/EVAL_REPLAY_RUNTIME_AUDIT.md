# Eval Replay Runtime Audit

Date: 2026-05-08

## Current Test Coverage

The repo already has strong unit and runtime tests for core graph smoke, provider tool binding, permissions, session persistence, tools, skills, Superpowers plugin policy, hooks, MCP stdio/resources/prompts, Langfuse trace scoping, subagents, and context providers. These tests call `AssistantGraphRuntime` directly in many places and use the fake provider plus local fixtures.

## Covered Runtime Surfaces

- Graph invoke/resume/stream through `AssistantGraphRuntime`.
- Fake provider deterministic text and `tool:<name> <json>` tool-call prompts.
- Permission interrupt/resume for write, shell, network, and MCP tool routes.
- Tool result persistence through `SessionStorage`.
- Skill lifecycle and plugin policy activation.
- Hook lifecycle and declarative plugin hook behavior.
- MCP stdio fake server integration.
- Subagent child graph lifecycle and child-run sidecar persistence.
- Context reference parsing, provider resolution, budget, and observability redaction.

## Missing Scenario Replay Layer

Existing tests prove individual paths but do not provide a reusable scenario format, fixture workspace setup, report writer, or CLI entrypoint for replaying acceptance scenarios. There is no way to run a named scenario like `mcp-echo` or `write-permission-reject` and get a structured pass/fail report that summarizes events, tool calls, permissions, skills, context fragments, MCP calls, subagents, and final response constraints.

## Stable Event Contracts

The following event contracts are stable enough for scenario assertions:

- `session_started`, `session_persisted`, `final_response`
- `model_message`
- `tool_call_started`, `tool_call_finished`, `tool_call_error`
- `permission_required`, `permission_resolved`
- `skill_started`, `skill_finished`
- `hook_started`, `hook_finished`, `hook_blocked`, `hook_error`
- `mcp_tool_call_started`, `mcp_tool_call_finished`, `mcp_tool_call_error`
- `subagent_started`, `subagent_event`, `subagent_finished`, `subagent_error`
- `context_fragment_added`, `context_resolution_error`, `context_budget_applied`

Assertions should use existence, subset matching, counts, and contains checks instead of exact full event equality.

## Provider And Fixture Strategy

The fake provider is the default because it runs deterministic graph/tool behavior without API keys. It supports normal text responses and `tool:<name> <json>` prompts, which is enough to drive file tools, permission interrupts, MCP tools, and subagent calls through the real graph.

Scenario workspaces should be copied from `evals/fixtures/workspaces/` into a temporary run directory. MCP scenarios should use the existing local fake stdio server fixture or an eval-local copy. Plugin scenarios should use local plugin fixtures only; no GitHub/network install is needed.

## Replay Through Current Runtime

The harness should build an `AppConfig` directly, not through `AppConfig.from_env()`, so project `.env` cannot influence evals. It should create a fresh `AssistantGraphRuntime(build_dependencies(config))` per scenario, use temporary storage, and call `runtime.invoke(...)` / `runtime.resume(...)` for every step. It must not call tools, skills, MCP service operations, or hooks directly to satisfy scenario behavior.

## Risks

- Weak mocks could hide graph regressions; scenario runner must use the real compiled graph.
- Brittle exact final-response assertions would create noisy failures; use contains/not-contains constraints.
- Local `.env` could enable real providers or network if the runner used `from_env`; avoid it.
- Report payloads could become large or leak secrets; summarize/redact and truncate excerpts.
- Eval run output should not be staged as source artifacts.
- MCP stdio processes must be local fixtures and cleaned up by existing MCP service behavior.
