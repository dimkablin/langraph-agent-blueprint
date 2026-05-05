# Tools Runtime Audit

## Post-Fix Status (2026-05-06)

Core tools now work through the full graph path with deterministic fake-provider tests and visible events. Ollama `qwen3:14b` was manually verified for native `read_file` tool calling through the same graph path.

| Tool | Post-fix status | Evidence / limitation |
| --- | --- | --- |
| `read_file` | `working` | Fake E2E and Ollama manual tool-call smoke. |
| `write_file` | `working` | JSON fake tool args, permission interrupt/resume, file written, events visible. |
| `edit_file` | `working` | Prior read persists across turns; approval resumes and edit is applied. |
| `notebook_read` | `working` | Existing tests and graph path. |
| `notebook_edit` | `working` | E2E approval test edits notebook JSON. |
| `glob` | `working` | Runtime smoke and tests. |
| `grep` | `working` | Uses `rg --json`; Windows drive-letter parsing fixed. |
| `bash` | `working` | Approval/resume test and runtime smoke. |
| `powershell` | `working_on_windows` | Fixed to invoke PowerShell explicitly; E2E test passes on Windows. |
| `web_fetch` | `disabled_by_config` by default | Requires network enablement and permission. |
| `web_search` | `disabled_by_config` / unavailable without provider | No longer returns empty success when no provider is configured. |
| `todo_write` | `working` | Persists todos and `/todo` restores them in later turns. |
| `skill` | `working_with_documented_limits` | Routes to skill graph, emits skill events, enforces allowed-tool scope. |
| `agent` | `working_with_documented_limits` | Still limited/synthetic child behavior. |
| `diagnostics` | `working` | `/doctor` now calls diagnostics service. |

## Overall Tool Finding

The tool classes and registry are real, and fake-provider deterministic prompts can exercise part of the graph loop. Real-provider model invocation cannot reach any tool because provider tool binding is absent.

Every tool status below distinguishes:

- direct/service behavior
- fake-provider graph behavior
- real model reachability
- event/persistence behavior

## Tool Table

| Tool | Class/file | Input schema | Output schema | Safety | Permission | Direct execution | Graph execution via fake provider | Real model execution | Events | Persistence | Status | Root cause | Fix needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `read_file` | `tools/file_tools.py` | `FileReadInput` | `FileReadOutput` | read_only | no | works; root confinement works | works | no Ollama call | lost except final | tool_calls yes | `partially_working` | provider not bound; events overwritten | Bind tools; add event reducer; return ToolMessage. |
| `write_file` | `tools/file_tools.py` | `FileWriteInput` | `FileWriteOutput` | write | yes | works | works with special fake syntax and approval | no | initial permission visible; later tool events lost | tool_calls yes | `partially_working` | fake generic JSON special-case misparses; provider not bound | Fix fake parser; bind tools; preserve events. |
| `edit_file` | `tools/file_tools.py` | `FileEditInput` | `FileEditOutput` | write | yes | works with read history or `allow_unread` | approval path works; no-prior-read errors correctly | no | lost except final | tool_calls yes | `partially_working` | read history stored only in metadata; no durable multi-turn read context | Persist read history; bind tools/events. |
| `notebook_read` | `tools/notebook_tools.py` | `NotebookReadInput` | `NotebookReadOutput` | read_only | no | works on valid `.ipynb` | works | no | lost except final | tool_calls yes | `partially_working` | provider/events gaps | Bind tools; improve invalid notebook error visibility. |
| `notebook_edit` | `tools/notebook_tools.py` | `NotebookEditInput` | `NotebookEditOutput` | write | yes | likely works if cell exists | not fully E2E audited | no | likely lost | likely | `unknown_needs_more_testing` | no runtime audit approval scenario yet | Add E2E fake-provider test. |
| `glob` | `tools/search_tools.py` | `GlobInput` | `GlobOutput` | read_only | no | works | works | no | lost except final | tool_calls yes | `partially_working` | provider/events gaps | Bind tools; add truncation. |
| `grep` | `tools/search_tools.py`, `services/search_service.py` | `GrepInput` | `GrepOutput` | read_only | no | broken on Windows rg absolute paths | broken in audit | no | lost except final | error persisted as tool_call | `broken` | `_grep_rg` splits `C:\path:line:text` by `:` and parses path segment as line number. | Use `rg --json` or robust Windows parser. |
| `bash` | `tools/shell_tools.py` | `ShellInput` | `ShellOutput` | shell | yes | works | works with approval/rejection | no | permission visible; execution events lost | tool_calls yes on execution | `partially_working` | provider/events gaps; coarse safety | Bind tools; preserve events; improve classifier. |
| `powershell` | `tools/shell_tools.py` | `ShellInput` | `ShellOutput` | shell | yes | implemented | not fully audited E2E | no | likely lost | likely | `unknown_needs_more_testing` | platform-specific test missing | Add Windows E2E approval test. |
| `web_fetch` | `tools/web_tools.py`, `services/web_service.py` | `WebFetchInput` | `WebFetchOutput` | network | yes | disabled by default | returns PermissionError when disabled | no | lost except final | tool_call error | `blocked_by_config` | expected config block; provider not bound | Mark disabled in model context unless enabled. |
| `web_search` | `tools/web_tools.py`, `services/web_service.py` | `WebSearchInput` | `WebSearchOutput` | network | yes | returns empty results if enabled | fake graph says "0 results" | no | lost except final | tool_calls yes | `blocked_by_config` | no search provider configured | Add provider or report unavailable, not "working". |
| `todo_write` | `tools/todo_tools.py` | `TodoWriteInput` | `TodoWriteOutput` | write | no | works | updates `todos` in same graph result | no | lost except final | todos saved | `partially_working` | state not restored across turns; provider not bound | Session restore and event reducer. |
| `agent` | `tools/agent_tools.py`, `services/agent_service.py` | `AgentInput` | `AgentOutput` | agent | no | synthetic child result | fake graph can call | no | lost except final | tool_calls yes | `partially_working` | no real child graph run | Implement child graph execution and merge. |
| `skill` | `tools/skill_tool.py` | `SkillToolInput` | `SkillToolOutput` | skill | no | returns skill prompt | fake graph routes to skill prompt | no | skill events lost | no skill record | `partially_working` | provider cannot call; skill runtime prompt-only | Provider binding and skill subgraph. |
| `diagnostics` | `tools/diagnostics_tools.py` | `DiagnosticsInput` | `DiagnosticsOutput` | read_only | no | works direct | model only via fake syntax | no | lost except final | tool_call if invoked | `registered_but_unreachable` | `/doctor` does not call it; provider not bound | Wire command and provider. |

## Additional Findings

### Path confinement

`read_file` blocks outside-root paths:

```text
tool:read_file {"path":"../outside.txt"}
final_response: Recovered from error: Path is outside allowed root: ...
```

### Permission flow

`write_file`, `edit_file`, and `bash` set `pending_confirmation` and interrupt. Resume approval/rejection works for deterministic fake-provider calls.

### Persistence

`tool_executor_node` writes `tool_calls.jsonl`. Example read_file session had:

```text
tool_calls.jsonl contains read_file record
events.jsonl contains only compact_decision event
```

The event persistence result demonstrates the `ui_events` overwrite issue.

### Notebook creation

There is no `notebook_create` tool. Creating a notebook can only happen through `write_file` with a valid `.ipynb` JSON payload once provider tool-calling works.
