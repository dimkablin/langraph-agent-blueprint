# Architecture Antipattern Audit

Date: 2026-05-07

## Summary

The runtime is graph-first overall. The main correctness path is expressed through `StateGraph` edges, and CLI/API chat adapters use `AssistantGraphRuntime` instead of calling tools directly. The main architecture debt is concentrated in service size, extension policy special-casing, and a few nodes that own business behavior instead of delegating to typed services or graph subflows.

## Findings

### P1: Superpowers Policy Is Hardwired Into The Graph Policy Node

Status: fixed in Batch 2 on 2026-05-07.

- File: `src/langgraph_agent_blueprint/graph/nodes/plugin_policy.py:7`
- File: `src/langgraph_agent_blueprint/plugins/superpowers.py:66`
- Problem: `plugin_policy_node` imported `choose_superpowers_activation` directly and called it for every turn.
- Why it matters: This makes the first real plugin policy a special case, not a generic plugin extension point. Adding another methodology plugin would require editing graph code or adding another policy branch.
- Fix: `PluginPolicyContribution`, `PluginPolicyContext`, and `PluginPolicyResult` now describe controlled plugin policies. `plugin_policy_node` evaluates registered policy contributions generically; Superpowers contributes `superpowers.default_methodology_policy`.

### P1: PluginService Owns Both Generic Plugin Discovery And Superpowers Adapter Logic

- File: `src/langgraph_agent_blueprint/services/plugin_service.py:15`
- File: `src/langgraph_agent_blueprint/services/plugin_service.py:103`
- File: `src/langgraph_agent_blueprint/services/plugin_service.py:127`
- Problem: The generic service imports Superpowers constants and adapter functions directly.
- Why it matters: Superpowers support works, but it couples external plugin discovery to one concrete plugin. The next plugin with bootstrap or policy metadata will likely add another branch.
- Suggested fix: Move known-layout adapters behind an adapter registry: `PluginManifestAdapter.detect(root) -> PluginContributionPatch`.

### P1: Skill Router Contains Skill-Specific Durable Memory Behavior

Status: fixed in Batch 2 on 2026-05-07.

- File: `src/langgraph_agent_blueprint/graph/nodes/skill_router.py:60`
- Problem: `skill_name == "remember"` wrote memory directly in the skill router.
- Why it matters: The skill router becomes a business-logic switchboard. Skill side effects do not use the same permission/tool/state-effect model as other runtime changes.
- Fix: `SkillInvocationService` returns typed `SkillEffect` records and `skill_router` delegates durable writes to a controlled skill-effect applier.

### P1: ToolExecutionContext Exposes The Whole Graph State To Tools

- File: `src/langgraph_agent_blueprint/tools/base.py:40`
- File: `src/langgraph_agent_blueprint/services/tool_execution_service.py:34`
- Problem: Tools receive `state=state` as part of `ToolExecutionContext`.
- Why it matters: The architecture says tools should not mutate graph state directly; however, the context hands every tool the mutable state dict. Core tools mostly behave, but new tools can bypass typed state effects accidentally.
- Suggested fix: Replace `state` with a frozen, minimal context DTO. If tools need state data, pass only whitelisted fields. Keep state writes in `ToolStateEffect`.

### P1: MCP Discovery Starts During Dependency Construction

Status: fixed in Batch 2 on 2026-05-07.

- File: `src/langgraph_agent_blueprint/dependencies.py:87`
- Problem: `build_dependencies` constructed `MCPService` and immediately called `mcp_service.discover()` to register tools.
- Why it matters: Discovery can start stdio MCP server processes for any runtime construction, including diagnostics/listing paths. This is explicit if config is present, but still surprising and heavy for a dependency factory.
- Fix: dependency construction now creates `MCPService` without discovery. `load_registries` and explicit diagnostics/commands perform discovery and register MCP tools.

### P2: Formal MCP Subgraph Adds Little Workflow Structure

- File: `src/langgraph_agent_blueprint/graph/subgraphs/mcp_graph.py:12`
- Problem: `mcp_graph` is a one-node wrapper around `tool_executor_node`.
- Why it matters: The docs imply a distinct MCP execution path, but the subgraph does not add resolve/call/format structure yet. This is acceptable for P0 behavior but weak as a reference architecture.
- Suggested fix: Expand to clear nodes when MCP grows: resolve contribution, call MCP, format result, cleanup/error path. Keep permission before the subgraph.

### P2: Large Services Are Approaching God-Service Shape

- Files: `src/langgraph_agent_blueprint/services/observability_service.py` (709 lines), `mcp_service.py` (438), `plugin_service.py` (413), `graph/builder.py` (345)
- Problem: These modules mix config/status, lifecycle, mapping, SDK/protocol adapters, and runtime facade code.
- Why it matters: They are still readable, but upcoming Langfuse/MCP/plugin growth will make changes risky.
- Suggested fix: Split by responsibility:
  - Observability: config/status, Langfuse factory, event mapper, scoped turn.
  - MCP: config parser, discovery service, invocation service, diagnostics.
  - Plugins: source install, manifest adapters, contribution discovery.
  - Builder: graph construction vs runtime facade.

### P2: AppDependencies Is A Very Wide Container

- File: `src/langgraph_agent_blueprint/dependencies.py:33`
- Problem: `AppDependencies` contains more than twenty dependencies and is passed into every node closure.
- Why it matters: This is pragmatic for now, but it increases coupling and makes it easy for nodes to reach across layers.
- Suggested fix: Group dependencies by runtime area or pass narrower node dependency DTOs to high-risk nodes.

### P2: Hook Dispatch Is Partly Graph-Owned, Partly Helper-Owned

- File: `src/langgraph_agent_blueprint/graph/hooks.py:35`
- File: `src/langgraph_agent_blueprint/graph/nodes/hook_runner.py`
- Problem: Hooks are called by lifecycle nodes, while `hook_runner` remains as a compatibility node for graph shape.
- Why it matters: The model is documented, but the extra node can confuse future contributors about where hooks are actually fired.
- Suggested fix: Either remove the compatibility node in a planned cleanup or rename it to make its current role explicit.

### P3: Source Tree Contains A BOM In CLI Module

- File: `src/langgraph_agent_blueprint/cli.py:1`
- Evidence: first bytes are `EF BB BF`.
- Problem: Normal `ast.parse(..., encoding="utf-8")` failed until read with `utf-8-sig`.
- Why it matters: Runtime imports work, but tooling may stumble.
- Suggested fix: Remove BOM in a formatting-only cleanup.

## Dependency Shape

A simple AST import graph found no Python module cycles inside `src/langgraph_agent_blueprint`.
