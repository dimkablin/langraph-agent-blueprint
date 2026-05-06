# Tools Runtime Audit

Current acceptance status as of 2026-05-06. Every required non-network tool was verified through the full model/tool graph loop, not only by direct service execution.

## Runtime Path

```text
user prompt -> model_call -> AIMessage.tool_calls -> pending_tool_calls
-> tool_router -> permission_gate when needed -> tool_executor
-> ToolMessage -> model_call -> final_response
-> ui_events -> persist_session/tool_calls.jsonl
```

## Current Tool Matrix

| Tool | Class/file | Safety | Permission | Direct/service status | Full graph status | Events | Persistence | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `read_file` | `tools/file_tools.py` | read-only | no | works | works with fake and Ollama | `tool_call_started`, `tool_call_finished` | tool_calls/session | `working` | Reads `README.md`; final answer includes `ACCEPTANCE_README_LINE`; ToolMessage appended. |
| `write_file` | `tools/file_tools.py` | write | yes | works | approval and rejection work | permission + tool events | tool_calls/permission decisions | `working` | Approval writes file; rejection leaves no file and returns rejected ToolMessage. |
| `edit_file` | `tools/file_tools.py` | write | yes | works | prior read + approval works | permission + tool events | tool_calls/read metadata | `working` | Exact replace changes `old value` to `new value`; missing text recovers with structured error. |
| `notebook_read` | `tools/notebook_tools.py` | read-only | no | works | works | tool events | tool_calls/session | `working` | Reads valid `notebook.ipynb`. |
| `notebook_edit` | `tools/notebook_tools.py` | write | yes | works | approval and edit work | permission + tool events | tool_calls/session | `working` | Edits cell to `print("edited acceptance final")` and notebook JSON remains valid. |
| `glob` | `tools/search_tools.py` | read-only | no | works | works | tool events | tool_calls/session | `working` | Finds `src\example.py` and `src\math_utils.py`. |
| `grep` | `tools/search_tools.py`, `services/search_service.py` | read-only | no | works | works | tool events | tool_calls/session | `working` | Relative `path=src` resolves under project root; `rg --json` avoids Windows drive-letter parsing failures. |
| `bash` | `tools/shell_tools.py` | shell | yes | works | JSON fake args and approval work | permission + tool events | tool_calls/permission decisions | `working` | `echo acceptance-shell` returns stdout after approval. |
| `powershell` | `tools/shell_tools.py` | shell | yes | works on Windows | works on Windows | permission + tool events | tool_calls/permission decisions | `working` | `Write-Output acceptance-powershell` returns stdout after approval. |
| `web_fetch` | `tools/web_tools.py` | network | yes | disabled by default; works when enabled | works with configured network and approval | permission + tool events | tool_calls/permission decisions | `working_with_provider_requirement` | Disabled mode reports config error. Enabled local HTTP fetch returns content and `untrusted` warning metadata. |
| `web_search` | `tools/web_tools.py` | network | yes | no provider configured | unavailable after approval | permission + error events | tool_calls/permission decisions | `disabled_by_config` | Returns `Web search provider is not configured`, not empty success. |
| `todo_write` | `tools/todo_tools.py` | state update | no | works | works | tool events | `todos.json` | `working` | Later `/todo` shows `final acceptance todo`. |
| `skill` | `tools/skill_tool.py` | skill | no | works | routes to skill graph | skill events | session/skill metadata | `working` | Structured `remember` args persist memory. |
| `agent` | `tools/agent_tools.py` | agent | no | limited | limited child result | child events | child_runs/session | `unsupported_optional` | Subagent remains limited/synthetic. |
| `diagnostics` | `tools/diagnostics_tools.py` | read-only | no | works | `/doctor` uses service | command events | diagnostics metadata | `working` | `/doctor` records diagnostics. |

## Fixes Confirmed During Final Acceptance

- Fake provider now treats `tool:bash {"command":"..."}` as JSON tool args instead of a literal shell command.
- Search tools now resolve relative `path` arguments under `project_root` before glob/grep execution.
- `web_fetch` now propagates untrusted-content warning metadata.

## Historical Audit Result

Before runtime fixes, provider tools were not bound, events were overwritten, grep failed on Windows absolute paths, and tool results were not returned as ToolMessages. Those rows are historical and replaced by the current matrix above.
