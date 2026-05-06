# Runtime Pipeline Audit

Current acceptance status as of 2026-05-06.

This document originally captured the pre-fix runtime audit. Historical findings are summarized at the end; the current sections below reflect verified runtime behavior after fixes and final acceptance.

## Runtime That Exists Now

The shared runtime is `AssistantGraphRuntime` in `src/langgraph_agent_blueprint/graph/builder.py`. CLI, API, frontend-facing endpoints, and tests call the same compiled LangGraph graph.

Main graph:

```text
START
-> bootstrap_config
-> load_registries
-> normalize_input
-> command_router
-> context_builder
-> model_call
-> tool_router
-> permission_gate/tool_executor/skill_graph/agent_graph/mcp_graph
-> hook_runner
-> compact_decision
-> compact_context or persist_session
-> finalize_response
-> END
```

The graph uses LangGraph nodes, conditional edges, checkpointer-backed interrupt/resume, and state reducers. Tool, command, skill, permission, compaction, and persistence workflows are not bypassed by CLI/API direct tool calls.

## Verified Runtime Paths

| Path | Current behavior | Evidence | Status |
| --- | --- | --- | --- |
| Normal chat | Input becomes HumanMessage, context is built, provider returns model response, session persists, final event emitted. | Fake smoke returned `Fake response: hello acceptance`; Ollama returned `OLLAMA_CHAT_OK`. | `working` |
| Slash commands | `/help`, `/clear`, `/compact`, `/resume`, `/export`, `/skills`, `/status`, `/cost`, `/config`, `/doctor`, `/memory`, `/todo` route through command registry/router and do not require LLM when local. | Command smoke passed; stream-json `/help` emitted command events. | `working` |
| Tool loop | Provider tool call is stored as `AIMessage.tool_calls`, routed, permissioned when needed, executed, appended as `ToolMessage`, then returned to model. | Fake and Ollama `read_file` returned `ACCEPTANCE_README_LINE`. | `working` |
| Permission loop | Write/edit/shell/network tools interrupt, resume on approval/rejection, emit events, and persist decisions. | `write_file` approve wrote file; reject did not write file. | `working` |
| Skill loop | `/skill` and SkillTool route through skill graph, emit skill events, narrow allowed tools, and persist state. | Built-in skill smoke emitted `skill_started`/`skill_finished`; `remember` wrote durable memory. | `working` / `working_prompt_driven` |
| Session lifecycle | Metadata, messages, events, tool calls, todos, memory refs, exports, and summaries persist under storage. | `resume-accept2` restored todo and continued. | `working` |
| Compaction | Manual `/compact` creates summary/status and emits compact events. | `Context compacted.` and `context_status.compacted=True`. | `working` |
| Streaming | Runtime stream emits JSONL event deltas. | CLI `--output stream-json /help` emitted multiple JSON records ending in `final_response`. | `working` |

## Provider Status

- `fake`: deterministic model/tool behavior for tests and local smoke.
- `ollama`: verified live with `qwen3:14b`; native `read_file` call reached the graph and returned a ToolMessage.
- `openai`, `openai_compatible`, `anthropic`: share the LangChain binding path and require configured providers/API keys for live use.

## Historical Audit Result

The original audit found these pre-fix blockers:

- providers did not bind tools or pass system context;
- tool results were not returned as ToolMessages;
- events were overwritten;
- project root could become storage root;
- skills were mostly prompt expansion;
- `/compact`, `/resume`, `/export`, and `/doctor` were incomplete;
- grep parsing broke on Windows paths.

Those findings drove the fix plan and are no longer the current runtime status. See `docs/FINAL_ACCEPTANCE_REPORT.md` and `docs/CAPABILITY_STATUS_MATRIX.md` for current acceptance evidence.
