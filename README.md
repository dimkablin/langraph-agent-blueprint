# claude-code-langgraph

Python/LangGraph implementation of the audited Claude Code-like coding assistant runtime.

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

Copy `.env.example` values into your environment. Tests and local smoke runs work with:

```bash
set LLM_PROVIDER=fake
set MODEL_NAME=fake-model
```

Supported provider names:

- `fake`
- `openai`
- `openai_compatible`
- `ollama`
- `anthropic`

## Run Interactive CLI

```bash
python -m claude_code_langgraph chat
```

The CLI calls the same LangGraph runtime as headless/API modes. Permission prompts are resumed through LangGraph interrupt/resume, not direct tool calls.

## Run Headless Query

```bash
python -m claude_code_langgraph query "hello"
python -m claude_code_langgraph query --output json "hello"
python -m claude_code_langgraph query --output stream-json "hello"
```

## Run React CLI Frontend

The browser frontend is a React terminal UI. It does not execute tools directly; it calls the graph-facing FastAPI endpoints `/chat`, `/approval`, `/commands`, `/skills`, and `/tools`.

Start the API:

```bash
uvicorn claude_code_langgraph.api.server:create_app --factory --host 127.0.0.1 --port 8000
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
python -m claude_code_langgraph query "Explain this project."
```

You can also use OpenAI-compatible Ollama endpoints through `LLM_PROVIDER=openai_compatible`.

Manual verification was also run with:

```bash
set LLM_PROVIDER=ollama
set OLLAMA_MODEL=qwen3:14b
python -m claude_code_langgraph query "Use read_file to read README.md and answer with its first line."
```

`qwen3:14b` successfully emitted a native `read_file` tool call through LangGraph, the graph executed the tool, appended a `ToolMessage`, and the model produced the final answer from the file content.

## Tests

```bash
python -m pytest
npm --prefix frontend run test:static
npm --prefix frontend run build
```

The test suite uses the fake provider and requires no real API keys, network, MCP server, or Ollama daemon.

Current final acceptance verification on 2026-05-06:

- `python -m pytest -q -rA`: passed, 73 collected tests.
- `npm.cmd --prefix frontend run test:static`: passed.
- `npm.cmd --prefix frontend run build`: passed outside sandbox after a Windows sandbox `spawn EPERM`.
- Runtime smoke in `test_runs/final-acceptance-workspace`: 36/36 fake-provider scenarios passed.
- Ollama `qwen3:14b`: native `read_file` tool call passed through LangGraph, produced a `ToolMessage`, and returned `ACCEPTANCE_README_LINE`.

## Graph Overview

The main runtime is a LangGraph `StateGraph`:

`bootstrap_config -> load_registries -> normalize_input -> command_router -> context_builder -> model_call -> tool_router -> permission_gate/tool_executor/subgraphs -> hook_runner -> compact_decision -> persist_session -> finalize_response`.

Tool-use loops, permission flow, skill invocation, subagents, compaction, memory, and session lifecycle are represented as graph nodes/subgraphs.

## Runtime Boundary Contracts

Runtime inputs and outputs are validated at layer boundaries with Pydantic DTOs, while LangGraph state remains plain JSON/checkpointer-safe dictionaries. Provider tool calls normalize into `ToolCall`, tool execution returns `ToolResult`, UI/storage events validate as `RuntimeEvent`, slash commands parse into `ParsedCommand`, permission interrupts use `PermissionRequest`, and skill args use skill-specific schemas.

See `docs/PYDANTIC_BOUNDARIES.md` for the contract map and extension rules.

## Tools

Core tools include file read/write/edit, notebook read/edit, glob, grep, bash, PowerShell, web fetch/search, todo write, agent, skill, MCP adapter, and diagnostics. Risky tools require permission unless policy allows them.

Examples with the fake provider:

```bash
python -m claude_code_langgraph query "tool:read_file {\"path\":\"README.md\"}"
python -m claude_code_langgraph query --output stream-json "tool:read_file {\"path\":\"README.md\"}"
```

Write/edit/shell/network tools request approval through LangGraph interrupt/resume. API and frontend receive `permission_required`; the CLI prompts interactively in `chat` mode.

## Skills

Skills are first-class `skill-name/SKILL.md` capabilities with frontmatter metadata. Built-ins include `debug`, `remember`, `simplify`, `skillify`, `stuck`, `update-config`, `verify`, and `batch`.

Skills can be invoked explicitly:

```bash
python -m claude_code_langgraph query "/skill remember project: Prefer pytest."
python -m claude_code_langgraph query "/memory"
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

Optional commands such as `/plugins`, `/mcp`, `/context`, `/rewind`, `/branch`, `/rename`, and `/tag` are recognized with documented limitations.

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

- MCP is an architectural/service abstraction with mockable registration and disabled-by-default behavior when no config exists.
- Plugin support validates local manifests and exposes contributions; marketplace install/update is not implemented.
- IDE/LSP is documented as architectural/minimal.
- Provider JSON repair is minimal. Native tool calling is tested through fake provider and manually verified with Ollama `qwen3:14b`.
- `web_search` is unavailable unless a real search provider is configured. It no longer returns empty success when no provider exists.
- `web_fetch` is disabled unless `NETWORK_ENABLED=true` and still requires permission. When enabled, fetched content is marked as untrusted in tool metadata.
- Subagent execution remains limited/synthetic compared with the rest of the graph runtime.
- Data analyst capabilities are optional extensions, not direct-port behavior.
