# Skills Runtime Audit

## Post-Fix Status (2026-05-06)

Skills are now graph-routed runtime capabilities instead of only registry entries:

- `/skill <name> ...` enters `skill_graph` from the main graph.
- `SkillTool` model calls route to the same skill graph.
- Skill lifecycle events are visible: `skill_started`, `skill_finished`.
- Skill metadata `allowed_tools` is applied to provider tool binding and enforced again in `tool_router`.
- Disallowed tools inside a skill scope are rejected with a structured tool result and `ToolMessage`.
- `remember` writes durable memory through `MemoryService`; `/memory` shows the stored note.
- Skill invocation metadata is stored in graph metadata and persisted with the session.

Status:

| Skill | Post-fix status | Evidence / limitation |
| --- | --- | --- |
| `batch` | `working_with_documented_limits` | Explicit invocation emits skill events and scoped tools; prompt-driven coordination. |
| `debug` | `working_with_documented_limits` | Explicit and SkillTool invocation reach skill graph. |
| `remember` | `working` | Writes durable memory and `/memory` reads it. |
| `simplify` | `working_with_documented_limits` | Uses scoped model/tool loop; edits still require approval. |
| `skillify` | `working_with_documented_limits` | Uses scoped model/tool loop; writes require approval. |
| `stuck` | `working_with_documented_limits` | Uses scoped context/model loop. |
| `update-config` | `working_with_documented_limits` | Uses scoped model/tool loop; config file writes require approval through file tools. |
| `verify` | `working_with_documented_limits` | Scoped to shell/search/read tools; shell commands require approval. |

Most skills remain prompt-driven capabilities, which matches the file-based `SKILL.md` design. They are no longer prompt-only shortcuts: graph routing, events, provider tool scope, tool-router enforcement, and persistence are active.

## Overall Finding

Skills are loaded and listed, but they are not yet full agentic skills. Current skill execution renders the `SKILL.md` body into a prompt, appends it as a `HumanMessage`, and calls the model. It does not enforce allowed tools, persist skill usage, or run a true skill subgraph with model/tool lifecycle.

`SkillTool` exists, but real providers cannot call it because tools are not bound.

## Skill Runtime Path

Actual explicit invocation path:

```text
/skill verify args
-> command_router sets active_skill
-> skill_router renders prompt and allowed_tools_override
-> context_builder -> model_call
-> final_response
```

Actual events visible:

```text
["final_response"]
```

Expected but missing:

```text
skill_started, skill_finished, tool_call_started, tool_call_finished, memory_updated, session_persisted
```

## Skill Table

| Skill | File path | Metadata loaded | Listed | Explicitly invokable | Invokable as model tool | Allowed tools respected | Events visible | State changed when expected | Persisted | Status | Runtime evidence | Root cause | Fix needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `batch` | `src/claude_code_langgraph/skills/definitions/batch/SKILL.md` | yes | yes | yes | no with Ollama | no | no | no child/todo coordination | no | `partially_working` | `/skill batch` renders prompt and allowed tools `agent,todo_write`. | Prompt-only skill graph; provider tools not bound. | Implement skill subgraph and allowed tool scope. |
| `debug` | `.../debug/SKILL.md` | yes | yes | yes | no | no | no | no diagnostics/search run | no | `partially_working` | Renders debug prompt. | No tool loop in skill context. | Same. |
| `remember` | `.../remember/SKILL.md` | yes | yes | yes | no | no | no | no memory write | no | `partially_working` | Renders memory prompt; `/memory` remains none. | MemoryService not invoked by skill runtime. | Add remember graph node/service write with permission policy. |
| `simplify` | `.../simplify/SKILL.md` | yes | yes | yes | no | no | no | no edit/read | no | `partially_working` | Renders simplify prompt. | No tools bound/enforced. | Same. |
| `skillify` | `.../skillify/SKILL.md` | yes | yes | yes | no | no | no | no file write | no | `partially_working` | Renders skillify prompt. | No permissioned write path. | Same. |
| `stuck` | `.../stuck/SKILL.md` | yes | yes | yes | no | no | no | no recovery state | no | `partially_working` | Renders stuck prompt. | No access to errors/todos beyond prompt. | Same. |
| `update-config` | `.../update-config/SKILL.md` | yes | yes | yes | no | no | no | no config write | no | `partially_working` | Renders update-config prompt. | Config service not called; no approval. | Add config update workflow behind tools/permission. |
| `verify` | `.../verify/SKILL.md` | yes | yes | yes | no | no | no | no shell evidence | no | `partially_working` | Renders verify prompt; no shell command runs. | Provider cannot call `bash`; skill graph prompt-only. | Provider binding + skill subgraph. |

## Specific Root Causes

1. `skill_router_node` returns `metadata.allowed_tools_override`, but no later node reads it to filter tools.
2. `SkillTool.run` returns prompt text as tool content instead of invoking a graph/subgraph.
3. `build_skill_graph` contains only `skill_router`; it has no model/tool/permission/persistence loop.
4. `ui_events` for `skill_started` and `skill_finished` are overwritten before final API/CLI responses.
5. No session storage writes explicit skill invocation records.

## Optional Skills

`loop`, `schedule`, `keybindings-help`, `lorem-ipsum`, `claude-api`, `claude-api-content`, and `claude-in-chrome` are recorded in `SkillRegistry.disabled`, but `/skills` does not show disabled skills separately.
