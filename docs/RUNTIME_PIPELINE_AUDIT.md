# Runtime Pipeline Audit

## Post-Fix Runtime Status (2026-05-06)

The runtime audit blockers have been fixed in implementation:

- CLI/API still call the same `AssistantGraphRuntime`.
- Graph events are append-preserved and visible to CLI/API/frontend.
- Real providers receive `SystemMessage` context and bound tool schemas.
- `AIMessage.tool_calls` are preserved.
- Tool execution appends `ToolMessage` and returns to `model_call`.
- Permission interrupt/resume emits and persists `permission_required` / `permission_resolved`.
- `project_root` defaults to the workspace/current directory, never `storage_dir`.
- Skills route through graph, apply allowed-tool scope, and enforce scope in `tool_router`.
- `/compact`, `/export`, `/resume`, `/doctor`, `/memory`, and `/todo` now perform real graph/service work.
- `grep` uses `rg --json` and handles Windows paths.
- `stream-json` consumes LangGraph value stream deltas.

Manual runtime smoke passed for fake provider and Ollama `qwen3:14b`, including a native Ollama `read_file` tool call.

Date: 2026-05-05

Scope: audit-only pass over the current `claude-code-langraph` Python/LangGraph implementation. Production runtime code was not changed during this pass.

## Evidence Commands

Existing tests:

```text
$env:PYTHONPATH='src'; python -m pytest
36 passed in 5.32s

npm.cmd --prefix frontend run test:static
ok - React CLI frontend exposes terminal shell and all hint surfaces
ok - API client calls graph-facing backend endpoints only
ok - JSX modules import React for Vite classic JSX runtime
```

Runtime probes used a temporary workspace outside the repository:

```text
%TEMP%\claude-code-langgraph-runtime-audit\workspace
%TEMP%\claude-code-langgraph-runtime-audit\storage
```

The probes explicitly set `project_root` and `cwd`; they did not rely on default `.storage` root behavior.

## Runtime That Actually Exists

The real runtime is `AssistantGraphRuntime` in `src/claude_code_langgraph/graph/builder.py`. CLI and API adapters call the same compiled graph for `/chat`, `query`, and interactive turns.

The graph nodes are present:

```text
bootstrap_config -> load_registries -> normalize_input -> command_router
-> context_builder -> model_call -> tool_router
-> permission_gate/tool_executor/skill_graph/agent_graph/mcp_graph
-> hook_runner -> compact_decision -> compact_context/persist_session
-> finalize_response
```

The graph shape is real LangGraph routing, not a Python `while` loop. However, several critical data contracts are missing or not wired into the model/provider/state layers, so most transferred capabilities are not truly agentic end-to-end.

## Normal Chat Path

Working path:

```text
CLI/API input -> create_initial_state -> normalize_input -> command_router
-> context_builder -> model_call -> tool_router(no tools)
-> compact_decision -> persist_session -> finalize_response
```

Evidence:

```text
fake_simple_chat final_response: Fake response: hello
ui_event_types: ["final_response"]
usage.provider: fake
```

Status: `partially_working`.

Reason: final response works, but streaming/node events are lost and system context is not passed to real providers.

## Tool Loop Path

Intended path:

```text
model_call -> pending_tool_calls -> tool_router -> permission_gate
-> tool_executor -> tool_results -> model_call -> final_response
```

Actual deterministic fake-provider path:

- `read_file`, `glob`, `notebook_read`, `todo_write` execute through graph when the fake prompt is `tool:<name> {json}`.
- `write_file`, `edit_file`, `bash` can trigger `permission_required` and resume.
- `tool_results` are returned in graph state.
- `tool_calls.jsonl` is written for executed tools.

Broken/missing pieces:

- Real providers are not given bound tools.
- Tool results are not returned as `ToolMessage` or provider-compatible tool-result messages.
- `AIMessage` created after a model tool call does not retain `tool_calls`.
- `ui_events` are overwritten, so `tool_call_started` / `tool_call_finished` generally disappear before API/CLI output.
- `persist_session` writes only whatever `ui_events` survived until that node.

Evidence:

```text
tool_read_file final_response: Tool read_file ok: # Audit Workspace...
tool_read_file tool_results: [{"name": "read_file", "status": "ok"}]
tool_read_file ui_event_types: ["final_response"]

message classes after read_file:
HumanMessage("tool:read_file ...")
AIMessage("Calling tool read_file")       # no tool_calls stored on message
AIMessage("Tool read_file ok: hello")     # no ToolMessage
```

Status: `partially_working` with `blocked_by_missing_state_reducer`, `blocked_by_missing_streaming_event`, and provider-specific `model_cannot_call`.

## Skill Loop Path

Intended path:

```text
skill file -> SkillLoader -> SkillRegistry -> /skills and model context
-> SkillTool or /skill -> skill_graph -> allowed_tools narrowing
-> model/tool loop under skill context -> events/persistence
```

Actual path:

- Built-in `SKILL.md` files load.
- `/skills` lists eight built-ins.
- `/skill verify ...` and other explicit skills render the skill prompt and append it as a `HumanMessage`.
- `metadata.allowed_tools_override` is set.

Broken/missing pieces:

- `allowed_tools_override` is never enforced by `tool_router`, `ToolRegistry`, or provider binding.
- Skill events are overwritten before final output.
- Skill invocation does not persist an invocation record.
- Skills do not run a real subgraph with prompt/model/tool lifecycle; they only turn into a prompt for the next model call.
- Real Ollama cannot invoke `SkillTool` because tools are not bound.

Evidence:

```text
/skill verify sample args
final_response: Fake response: Identify the command that proves the claim...
metadata.allowed_tools_override: ["bash", "powershell", "grep", "glob", "read_file"]
ui_event_types: ["final_response"]
tool_results: []
```

Status: `partially_working` / `registered_but_unreachable` for model-driven skill use.

## Command Loop Path

Working path:

```text
user input "/command" -> parse_slash_command -> CommandRegistry
-> command_router -> local response/prompt/skill metadata
-> persist_session -> finalize_response
```

Local commands are reachable and do not need the LLM. Several are placeholders.

Evidence:

```text
/help -> Available commands: /branch, /clear, /compact, ...
/skills -> Available skills: batch, debug, remember, simplify, skillify, stuck, update-config, verify
/rewind -> /rewind is recognized but not implemented in the initial Python port.
```

Status: mixed. See `docs/COMMANDS_RUNTIME_AUDIT.md`.

## Main Root Causes

P0 blockers:

1. Provider layer ignores `system_context` and `tools`.
2. Provider layer does not call `bind_tools` or equivalent for Ollama/OpenAI/OpenAI-compatible/Anthropic.
3. Tool results are not returned to the model as `ToolMessage` or provider-compatible tool results.
4. `ui_events`, `tool_results`, `permission_decisions`, and several list-like fields lack append reducers and are overwritten.
5. Default dependency construction sets `project_root` to `storage_dir` when `project_root` is absent.
6. Skill execution is prompt expansion only; it does not enforce allowed tools or persist skill lifecycle.
7. Streaming adapter is not true streaming; it invokes the graph to completion and yields the final state's surviving `ui_events`.

P1 blockers:

1. `grep` parsing breaks on Windows absolute paths containing `C:\...`.
2. `/compact` sets `compact_requested`, but final visible behavior is a fake model answer plus hidden/lost compaction events.
3. `/export` records metadata but does not call `ExportService`.
4. `/resume` local command records intent but does not restore graph state.
5. `web_search` returns empty results when network is enabled because no provider is configured.
6. `notebook_create` is absent; notebook creation can only happen through `write_file` if the model can call it.

## What Is Actually Working End-to-End

Strictly working or mostly working with deterministic fake-provider paths:

- Simple chat final response.
- Local slash command parsing and immediate responses.
- Registry snapshots for tools, skills, commands.
- Read-only file path confinement for `read_file`.
- `read_file`, `glob`, `notebook_read`, `todo_write` execution through fake-provider tool-call syntax.
- Permission interrupt is created for `write_file`, `edit_file`, and `bash`.
- Approval/resume can execute `write_file` and `bash` when fake-provider arguments are valid.
- Rejection/resume returns a rejected tool result.
- `tool_calls.jsonl` is written by `tool_executor`.

## What Exists Mostly Formally

- Real-provider tool calling.
- Real-provider skill invocation.
- Tool/skill events as visible stream.
- Skill allowed-tools narrowing.
- Memory/remember skill state mutation.
- Manual `/compact` user-visible compaction.
- `/export` command execution.
- `/resume` command continuation.
- MCP and plugin runtime integration beyond mock/discovery abstractions.
- Web search provider.
- Subagent as real child graph; current service returns a synthetic result.
