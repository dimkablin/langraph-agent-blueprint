# Skills Runtime Audit

Current acceptance status as of 2026-05-06. The old audit found prompt-only skill behavior; current verification shows explicit skill invocations and SkillTool invocations reach the graph skill route, emit events, enforce allowed-tool scope, and persist session state.

## Runtime Path

```text
SKILL.md -> SkillLoader -> SkillRegistry -> /skills or SkillTool
-> command_router/tool_router -> skill_graph node
-> skill_started event -> allowed_tools_override
-> skill prompt/model path or remember memory write
-> skill_finished event -> persist_session/finalize_response
```

## Current Skill Matrix

| Skill | File | Metadata loaded | Listed by `/skills` | Explicit invocation | Model SkillTool invocation | Allowed tools enforced | Events visible | Persisted | Current status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `batch` | `src/claude_code_langgraph/skills/definitions/batch/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working_prompt_driven` | `/skill batch acceptance input` emitted `skill_started` and `skill_finished`; scoped to `agent,todo_write`. |
| `debug` | `src/claude_code_langgraph/skills/definitions/debug/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working_prompt_driven` | SkillTool path reaches skill graph and adds ToolMessage. |
| `remember` | `src/claude_code_langgraph/skills/definitions/remember/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working` | `tool:skill {"skill":"remember","args":{"text":"Dima 228","scope":"project"}}` persisted memory; `/memory` showed `Dima 228`. |
| `simplify` | `src/claude_code_langgraph/skills/definitions/simplify/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working_prompt_driven` | Explicit invocation uses skill graph; edits remain permissioned through `edit_file`. |
| `skillify` | `src/claude_code_langgraph/skills/definitions/skillify/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working_prompt_driven` | Explicit invocation uses skill graph; writes remain permissioned through `write_file`. |
| `stuck` | `src/claude_code_langgraph/skills/definitions/stuck/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working_prompt_driven` | Explicit invocation uses skill graph and current state context. |
| `update-config` | `src/claude_code_langgraph/skills/definitions/update-config/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working_prompt_driven` | Explicit invocation uses skill graph; config file edits remain permissioned. |
| `verify` | `src/claude_code_langgraph/skills/definitions/verify/SKILL.md` | yes | yes | yes | yes | yes | yes | yes | `working_prompt_driven` | Explicit invocation scoped to shell/search/read tools; shell still requires approval. |

## Allowed-Tools Narrowing

Acceptance and regression tests verify that a disallowed tool inside a skill scope is rejected by `tool_router`, receives a structured ToolMessage/policy result, and is not executed.

## Typed Skill Args

Local and real providers may return nested tool arguments. `SkillInvocationService` now validates them through per-skill Pydantic schemas before rendering prompts. Invalid args produce a structured ToolMessage error and do not execute the skill. Example:

```text
{"skill":"remember","args":{"text":"Dima 228","scope":"project"}}
```

validates as `RememberSkillArgs` and formats for prompt interpolation as:

```text
text: Dima 228
scope: project
```

String args are mapped explicitly by skill name, for example `remember this` becomes `RememberSkillArgs(text="remember this", scope="session")`.

## Historical Audit Result

Before the fixes, skills were loaded and listed but mostly behaved as prompt expansion. That status is historical only.
