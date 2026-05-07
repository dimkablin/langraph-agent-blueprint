# LangGraph Agent Blueprint

LangGraph Agent Blueprint is a reference implementation of a production-style agent runtime built with Python and LangGraph.

It demonstrates:

- graph-first agent orchestration
- provider tool-calling
- typed Pydantic runtime boundaries
- metadata-driven tools
- skills
- slash commands
- hooks
- human-in-the-loop permissions
- session persistence
- streaming events
- memory
- compaction
- real child graph subagents

This project ports the behavior described in:

- `docs/SOURCE_AUDIT.md`
- `docs/SKILLS_AUDIT.md`
- `docs/FEATURE_TRACEABILITY_MATRIX.md`
- `docs/MIGRATION_SPEC.md`

The audited source is `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project`. The earlier `claude-like-project` path does not exist.

## What This Is

This is a Claude Code-like terminal/headless coding assistant. It is not a browser React data analyst app. The audit found no first-class dataset ingestion, dataframe profiling, dataset Q&A, chart artifact editor, or browser artifact workflow in the source. Those are documented as optional extensions, not direct-port features.

## Install

```bash
python -m pip install -e ".[test,api,openai,ollama]"
```

Anthropic support is optional:

```bash
python -m pip install -e ".[anthropic]"
```

## Configure

Copy `.env.example` to `.env` in the project root or set the variables in your shell. The CLI/API load project-root `.env` automatically, and process environment variables take precedence. Tests and local smoke runs work with:

```bash
set LLM_PROVIDER=fake
set MODEL_NAME=fake-model
```

OpenAI-compatible example:

```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=http://localhost:11434/v1
OPENAI_COMPATIBLE_MODEL=qwen3:14b
OPENAI_COMPATIBLE_API_KEY=not-needed
```

Supported provider names:

- `fake`
- `openai`
- `openai_compatible`
- `ollama`
- `anthropic`

## Run Interactive CLI

```bash
lg-agent chat
```

The CLI calls the same LangGraph runtime as headless/API modes. Permission prompts are resumed through LangGraph interrupt/resume, not direct tool calls.

## Run Headless Query

```bash
lg-agent query "hello"
lg-agent query --output json "hello"
lg-agent query --output stream-json "hello"
```

Other CLI entrypoints:

```bash
lg-agent skills list
lg-agent tools list
lg-agent plugins list
lg-agent doctor
```

## MCP Client Runtime

MCP servers are optional and explicit. Phase 2 supports local stdio MCP clients for `initialize`, `tools/list`, `tools/call`, `resources/list/read`, and `prompts/list/get`. Streamable HTTP is modeled but reported as unsupported in this phase.

Example environment config:

```powershell
$env:MCP_CONFIG_JSON = '{"servers":{"fake":{"enabled":true,"transport":"stdio","command":"python","args":["tests/fixtures/mcp/fake_mcp_server.py"]}}}'
lg-agent query "/mcp"
lg-agent query "/mcp tools"
lg-agent query "/doctor"
```

Discovered tools register as `mcp.<server>.<tool>` and route through `ToolRuntimeMetadata(kind="mcp", route="mcp_graph")`. Unknown MCP tools require approval by default and cannot bypass `PermissionService`. Resource and prompt content is marked external/untrusted. See `docs/MCP.md`.

## Optional: Langfuse Observability

Langfuse tracing is optional and disabled by default. Install the extra and set keys when you have a Langfuse project:

```powershell
python -m pip install -e ".[observability]"
$env:LANGFUSE_ENABLED = "true"
$env:LANGFUSE_PUBLIC_KEY = "pk-lf-..."
$env:LANGFUSE_SECRET_KEY = "sk-lf-..."
$env:LANGFUSE_BASE_URL = "https://your-langfuse-host"
lg-agent doctor
lg-agent query "hello"
```

The graph attaches Langfuse callbacks at invoke/stream boundaries and maps critical RuntimeEvents for tools, skills, hooks, MCP, permissions, compaction, persistence, final responses, and errors. If disabled, missing, or misconfigured, normal runtime behavior continues with no-op observability. `/doctor`, `/config`, and `/observability` redact keys. See `docs/OBSERVABILITY.md`.

Trace scoping is turn-based: one user turn creates one top-level Langfuse trace, while an interactive `lg-agent chat` process groups all turn traces under one shared Langfuse session id. Runtime events are scoped as child observations or compact metadata, not separate top-level `runtime.*` traces. Full local project paths are hidden by default unless `LANGFUSE_INCLUDE_PROJECT_PATHS=true`.

## Subagents

The `agent` tool launches a real child graph run. Child runs get isolated session/thread ids, a narrowed allowed-tools scope, normal permission routing, parent-linked events, and persisted child-run metadata/result records. Child read-only work can complete inside the child graph; child side-effect approval/resume is guarded and returns a structured error until nested approval UX is implemented.

```bash
lg-agent query "tool:agent {\"prompt\":\"tool:read_file {\\\"path\\\":\\\"README.md\\\"}\",\"allowed_tools\":[\"read_file\"],\"name\":\"reader\"}"
```

See `docs/SUBAGENTS.md`.

## Optional: Superpowers Plugin

Superpowers can be installed as an external plugin contribution. Git install/update is explicit network work, so enable network first:

```powershell
$env:NETWORK_ENABLED = "true"
lg-agent plugins install superpowers@git+https://github.com/obra/superpowers.git#v5.1.0
lg-agent plugins list
lg-agent skills list
```

When enabled, Superpowers skills are registered as `superpowers/<skill-name>`, `superpowers/using-superpowers` bootstrap context is injected at session start, and obvious new development prompts activate `superpowers/brainstorming` through LangGraph before code is written. See `docs/SUPERPOWERS_PLUGIN.md`.

## Run React CLI Frontend

The browser frontend is a React terminal UI. It does not execute tools directly; it calls the graph-facing FastAPI endpoints `/chat`, `/approval`, `/commands`, `/skills`, and `/tools`.

Start the API:

```bash
uvicorn langgraph_agent_blueprint.api.server:create_app --factory --host 127.0.0.1 --port 8000
```

Start the frontend:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Set a custom backend URL with:

```bash
set VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Run With Ollama

Install and start Ollama, then pull a model:

```bash
ollama pull llama3.1
set LLM_PROVIDER=ollama
set OLLAMA_MODEL=llama3.1
lg-agent query "Explain this project."
```

You can also use OpenAI-compatible Ollama endpoints through `LLM_PROVIDER=openai_compatible`.

Manual verification was also run with:

```bash
set LLM_PROVIDER=ollama
set OLLAMA_MODEL=qwen3:14b
lg-agent query "Use read_file to read README.md and answer with its first line."
```

`qwen3:14b` successfully emitted a native `read_file` tool call through LangGraph, the graph executed the tool, appended a `ToolMessage`, and the model produced the final answer from the file content.

## Tests

```bash
python -m pytest
npm --prefix frontend run test:static
npm --prefix frontend run build
```

The test suite uses the fake provider and a local fake stdio MCP server fixture. It requires no real API keys, network, external MCP server, or Ollama daemon.

Current final acceptance verification on 2026-05-06:

- `python -m pytest -q`: passed.
- `npm.cmd --prefix frontend run test:static`: passed.
- `npm.cmd --prefix frontend run build`: previously passed outside sandbox after a Windows sandbox `spawn EPERM`.
- Runtime smoke in `test_runs/final-acceptance-workspace`: 36/36 fake-provider scenarios passed.
- Ollama `qwen3:14b`: native `read_file` tool call passed through LangGraph, produced a `ToolMessage`, and returned `ACCEPTANCE_README_LINE`.

## Graph Overview

The main runtime is a LangGraph `StateGraph`:

`bootstrap_config -> load_registries -> normalize_input -> command_router -> plugin_policy/context_builder/skill_graph -> model_call -> tool_router -> permission_gate/tool_executor/subgraphs -> compact_decision -> persist_session -> finalize_response`.

Tool-use loops, permission flow, skill invocation, hooks, subagents, compaction, memory, and session lifecycle are represented as graph nodes/subgraphs. Hook dispatch is owned by the graph nodes that reach each lifecycle point.

## Runtime Boundary Contracts

Runtime inputs and outputs are validated at layer boundaries with Pydantic DTOs, while LangGraph state remains plain JSON/checkpointer-safe dictionaries. Provider tool calls normalize into `ToolCall`, tool execution returns `ToolResult`, UI/storage events validate as `RuntimeEvent`, slash commands parse into `ParsedCommand`, permission interrupts use `PermissionRequest`, skill args use skill-specific schemas, tools declare `ToolPermissionMetadata` / `ToolRuntimeMetadata`, plugins validate `PluginContribution`, hooks validate `HookContribution` / `HookResult`, MCP validates server/tool/resource/prompt DTOs, and observability validates `LangfuseConfig` / `TraceContext` / `TraceMetadata`.

See `docs/PYDANTIC_BOUNDARIES.md` for the contract map and extension rules.

## Hooks

Hooks are graph-owned lifecycle extension points for plugins, observability, policy, skills, tools, MCP, and future frontend integrations. Graph nodes call `HookService` at typed lifecycle points such as `user_prompt`, `pre_model`, `post_model`, `pre_tool`, `post_tool`, `permission_request`, `permission_resolved`, `pre_skill`, and `post_skill`.

External plugin hooks are declarative and data-only. They can add marked system context, metadata, events, or block a route, but they cannot execute scripts, mutate arbitrary graph state, or bypass tool permissions. Inspect registered hooks with:

```bash
lg-agent query "/hooks"
```

See `docs/HOOKS.md`.

## Tools

Core tools include file read/write/edit, notebook read/edit, glob, grep, bash, PowerShell, web fetch/search, todo write, agent, skill, MCP adapter, and diagnostics. Tool names are registry/provider identity only; permission action/risk, runtime route, plan-mode behavior, network requirement, and state effects come from tool metadata. Risky tools require permission unless policy allows them. Tools receive a minimal read-only execution context and return typed state effects; they do not receive mutable whole graph state.

Examples with the fake provider:

```bash
lg-agent query "tool:read_file {\"path\":\"README.md\"}"
lg-agent query --output stream-json "tool:read_file {\"path\":\"README.md\"}"
```

Write/edit/shell/network tools request approval through LangGraph interrupt/resume. API and frontend receive `permission_required`; the CLI prompts interactively in `chat` mode. Confirmation payloads are built from metadata and redact secret-like args recursively.

## Skills

Skills are first-class `skill-name/SKILL.md` capabilities with frontmatter metadata. Built-ins include `debug`, `remember`, `simplify`, `skillify`, `stuck`, `update-config`, `verify`, and `batch`.

External plugin skills are namespaced, for example `superpowers/brainstorming`. Plugin skills are loaded through `PluginService` and `SkillRegistry`, not copied into bundled definitions.

Skills can be invoked explicitly:

```bash
lg-agent query "/skill remember project: Prefer pytest."
lg-agent query "/skill superpowers/brainstorming Build a React todo list."
lg-agent query "/memory"
```

Skill invocation goes through the graph skill route, emits `skill_started` / `skill_finished`, filters provider-bound tools to the skill's `allowed_tools`, and enforces that scope in `tool_router`.

## Commands

Slash commands are routed through `CommandRegistry` and `command_router`:

- `/help`
- `/clear`
- `/compact`
- `/resume`
- `/export`
- `/skills`
- `/status`
- `/cost`
- `/config`
- `/doctor`
- `/memory`
- `/todo`
- `/plugins`
- `/hooks`
- `/mcp`
- `/observability`

Optional commands such as `/context`, `/rewind`, `/branch`, `/rename`, and `/tag` are recognized with documented limitations.

Required commands now perform real runtime work: `/compact` compacts context, `/export` writes a transcript, `/resume` restores session state, `/doctor` runs diagnostics, `/todo` reads persisted todos, and `/memory` reads durable memory.

## Permissions

Permission modes:

- `default`
- `accept_edits`
- `bypass_read_only`
- `plan`
- `strict`

Write/edit/shell/network/MCP/plugin side effects use conservative defaults. The graph stores `pending_confirmation`, interrupts, and resumes after approval or rejection.

## Session Storage

Sessions are stored under `.storage/projects/{project_hash}/sessions/{session_id}/`:

- `metadata.json`
- `events.jsonl`
- `tool_calls.jsonl`
- `messages.json`
- `todos.json`
- `memory_refs.json`
- `exports/`
- `large_outputs/`

## Limitations

- MCP client support currently covers stdio servers and core tools/resources/prompts operations. Streamable HTTP, OAuth, automatic discovery, MCP server mode, and prompt-to-skill registration are not implemented yet.
- Plugin support validates local manifests and exposes contributions; marketplace install/update is not implemented.
- IDE/LSP is documented as architectural/minimal.
- Provider JSON repair is minimal. Native tool calling is tested through fake provider and manually verified with Ollama `qwen3:14b`.
- `web_search` is unavailable unless a real search provider is configured. It no longer returns empty success when no provider exists.
- `web_fetch` is disabled unless `NETWORK_ENABLED=true` and still requires permission. When enabled, fetched content is marked as untrusted, private/internal hosts are blocked unless `WEB_FETCH_ALLOW_PRIVATE_HOSTS=true`, and response bodies are capped by `WEB_FETCH_MAX_BYTES`.
- The fake provider keeps a few shorthand aliases (`tool:bash echo hi`, `tool:write_file path content`, `tool:agent ...`) for deterministic tests; the generic supported contract is `tool:<name> <json args>`, and these aliases do not define production permission/routing semantics.
- Subagent execution is real/sequential for local child graph runs. Parallel/background teams and nested approval resume remain future work.
- Data analyst capabilities are optional extensions, not direct-port behavior.
