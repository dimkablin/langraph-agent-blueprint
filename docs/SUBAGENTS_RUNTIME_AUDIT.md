# Subagents Runtime Audit

Current audit date: 2026-05-07

This is the short pre-implementation audit for Phase 5 real subagents/task lifecycle.

## Current AgentTool

`src/langgraph_agent_blueprint/tools/agent_tools.py` currently exposes a model-callable `agent` tool with:

- `AgentInput(prompt: str, agent_type: str = "default")`
- `AgentOutput(child_run: dict[str, object])`
- `ToolRuntimeMetadata(kind="agent", route="agent_graph", state_effects=["append_child_run"])`
- medium-risk agent permission metadata

The tool body calls `AgentService.run_child(...)` directly and returns the service result. In normal main graph routing, `tool_router` sends `agent` calls to `agent_graph`, so the tool body's direct call is not the primary graph path. It still represents the same synthetic behavior if executed through `ToolExecutionService`.

## Current AgentService

`src/langgraph_agent_blueprint/services/agent_service.py` currently generates a child id and returns:

- `status: completed`
- original prompt
- `result: "Subagent completed: ..."`
- `parent_session_id`

It does not run a child graph, isolate state, call a model, invoke tools, persist a child transcript, or enforce subagent-specific tool scopes.

## Current agent_graph

`src/langgraph_agent_blueprint/graph/subgraphs/agent_graph.py` is a one-node subgraph:

```text
START -> agent_run -> END
```

The node reads the first pending `agent` tool call, calls `deps.agent_service.run_child(prompt, state)`, appends a synthetic child run, creates a synthetic `ToolResult`, emits `subagent_started` and `subagent_finished`, clears pending tool calls, and returns to the parent model loop.

## Current State Fields

`AssistantState` already has:

- `child_runs: Annotated[list[dict[str, Any]], append_list]`
- `tasks`
- `ui_events`
- `tool_results`
- `metadata`

There are no typed subagent boundary models yet. Child run records are raw dictionaries.

## Current Events

Current subagent events:

- `subagent_started`
- `subagent_finished`

They are emitted by the synthetic `agent_graph`. There are no `subagent_error`, `subagent_cancelled`, `subagent_timeout`, or forwarded child events.

## Current Persistence

Parent sessions persist normal messages/events/tool calls through `SessionStorage`. There is no child-run storage layout, no child transcript persistence, and parent metadata does not include durable child-run references beyond in-memory/session-state `child_runs`.

## Current Observability

Subagent events are ordinary `RuntimeEvent` records, so Langfuse can see the synthetic start/finish events. There is no child trace context or child run metadata linking a real child graph to the parent trace.

## Synthetic/Limited Behavior

The current subagent path is limited because:

- `AgentService.run_child()` does not run a model or graph.
- No child graph state is forked.
- Child ids/thread ids/session ids are not modeled.
- Child allowed-tools scope is not enforced.
- Child permissions cannot be requested because no child tools are run.
- No child transcript/result is persisted.
- No recursion/depth guard exists because no recursion is possible yet.
- Parent receives a synthetic tool result rather than a controlled merge from real child execution.

## Phase 5 Gaps To Close

Phase 5 should add:

- Typed `SubagentRequest`, `ChildRunMetadata`, `SubagentResult`, and merge policy models.
- Agent tool schema mapped to `SubagentRequest`.
- Child state creation with validated child ids and no shared mutable parent lists.
- Sequential real child graph execution through LangGraph.
- Allowed-tools narrowing that cannot broaden parent/skill scope.
- Recursion/depth guard.
- Conservative handling for child side effects: no permission bypass.
- Child run metadata/result persistence.
- Parent-visible subagent events and child event summaries.
- Langfuse-scoped subagent runtime events.

Nested approval/resume for child side effects may remain limited in this phase if it cannot be supported cleanly; the required safety rule is that child side effects must not execute without the normal permission path.

