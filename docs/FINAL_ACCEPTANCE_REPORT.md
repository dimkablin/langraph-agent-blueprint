# Final Acceptance Report

Date: 2026-05-06

Project root: `C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint`

Acceptance workspace: `C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint\test_runs\final-acceptance-workspace`

## Scope

This report verifies the current Python/LangGraph Claude Code-like assistant runtime after the runtime-audit fixes. It does not treat historical audit tables as current status. Current status is based on tests and live smoke runs performed against the acceptance workspace.

## Document Contradictions Found

The following documents mixed current post-fix claims with old audit rows that still said `broken`, `partially_working`, or `registered_but_unreachable`:

- `docs/CAPABILITY_STATUS_MATRIX.md`
- `docs/COMMANDS_RUNTIME_AUDIT.md`
- `docs/SKILLS_RUNTIME_AUDIT.md`
- `docs/TOOLS_RUNTIME_AUDIT.md`
- `docs/PROVIDER_TOOL_CALLING_AUDIT.md`

They were updated so the main tables now describe current acceptance status. Historical audit findings are summarized only as historical context.

## Verification Commands

| Command | Result |
| --- | --- |
| `python -m pytest -q -rA` | passed, 73 collected tests |
| `npm.cmd --prefix frontend run test:static` | passed |
| `npm.cmd --prefix frontend run build` | passed outside sandbox after sandbox run failed with Windows `spawn EPERM` |
| `lg-agent query "/help" --output stream-json` with `PYTHONPATH=src` | passed, emitted multiple JSONL events ending in `final_response` |

## Runtime Smoke Summary

All smoke scenarios below used `project_root = C:\Users\dimka\Documents\PROJECTS\langgraph-agent-blueprint\test_runs\final-acceptance-workspace`, not `.storage`.

| Scenario | Provider | Expected | Actual evidence | Result |
| --- | --- | --- | --- | --- |
| Basic chat | fake | final response, persisted session | `Fake response: hello acceptance`, `final_response` event | pass |
| `/help` | fake | command events and command list | listed active commands and unsupported optional commands | pass |
| `/status` | fake | correct project root, cwd, storage | showed acceptance workspace and `.storage_acceptance2` separately | pass |
| `/config` | fake | redacted effective config and paths | showed project root and separate storage dir | pass |
| `/doctor` | fake | real diagnostics service | `metadata.diagnostics` present | pass |
| `/clear` | fake | clears messages | final response `Conversation cleared.`, messages empty | pass |
| `/compact` | fake | compaction path, summary event | final response `Context compacted.`, `compact_finished` event | pass |
| `/export` | fake | transcript file | export file under `.storage_acceptance2\exports\...md` exists | pass |
| `/resume` | fake | restore usable state | resumed `resume-accept2`, restored todo `resume todo` | pass |
| `read_file` | fake | model tool call, ToolMessage, final answer | final answer contained `ACCEPTANCE_README_LINE` | pass |
| `write_file` approve | fake | permission, resume, file written | `created_approve2.txt` written after approval | pass |
| `write_file` reject | fake | permission, resume, no write | rejected final response and no file created | pass |
| `edit_file` | fake | prior read + approval | `old value` changed to `new value` | pass |
| `edit_file` missing text | fake | structured error recovery | `Recovered from error: old_text was not found...` | pass |
| `notebook_read` | fake | notebook cells read | final response `Tool notebook_read ok: Read notebook...` | pass |
| `notebook_edit` | fake | approval and valid JSON preserved | notebook cell changed to `print("edited acceptance final")` | pass |
| `glob` | fake | finds `src/*.py` | found `src\example.py` and `src\math_utils.py` | pass |
| `grep` | fake | relative path under project root | found `src\math_utils.py:1: def add...` | pass |
| `bash` | fake | approval and shell output | final response `Tool bash ok: acceptance-shell` | pass |
| `powershell` | fake | approval and PowerShell output | final response `Tool powershell ok: acceptance-powershell` | pass |
| `web_fetch` disabled | fake | honest disabled error | `Network access is disabled by configuration` | pass |
| `web_fetch` enabled | fake | approval, fetch, untrusted metadata | local HTTP response `local web acceptance`, metadata warning contains `untrusted` | pass |
| `web_search` no provider | fake | unavailable, not empty success | `Web search provider is not configured` | pass |
| `todo_write` | fake | persistent todo | later `/todo` showed `final acceptance todo` | pass |
| Built-in skills | fake | skill graph events and scoped runtime | `skill_started` and `skill_finished` for batch/debug/simplify/skillify/stuck/update-config/verify | pass |
| `remember` typed args | fake | durable memory from typed object args | `/memory` showed `Dima 228` from `{"text":"Dima 228","scope":"project"}` | pass |
| Stream adapter | fake | multiple events, final last | 7 events, last `final_response` | pass |

## Ollama Smoke

Ollama was available at `http://localhost:11434`; installed models included `qwen3:14b`.

Environment:

```text
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:14b
OLLAMA_BASE_URL=http://localhost:11434
```

Prompt:

```text
Use the read_file tool to read README.md. Do not answer from memory. After the tool result, answer with the first line only.
```

Evidence:

- `AIMessage.tool_calls`: `read_file` with args `{"path": "README.md"}`
- `ToolMessage`: matching `tool_call_id`, content included `ACCEPTANCE_README_LINE`
- final response: `ACCEPTANCE_README_LINE`
- event stream contained `tool_call_started`, `tool_call_finished`, `session_persisted`, `final_response`

Result: pass.

## Final Capability Counts

Required slash commands:

- `working`: 12
- `broken`: 0

Required tools:

- `working`: 11
- `disabled_by_config`: 1 (`web_search` without a provider; `web_fetch` is disabled when network is off and working when enabled)
- `disabled_by_platform`: 0 on Windows
- `broken`: 0

Required skills:

- `working`: 1 (`remember`)
- `working_prompt_driven`: 7 (`batch`, `debug`, `simplify`, `skillify`, `stuck`, `update-config`, `verify`)
- `broken`: 0

## Remaining Limitations

- `web_search` requires a real configured search provider.
- MCP remains optional and disabled when no MCP config exists.
- Plugin discovery validates manifests, but marketplace install/update and rich contribution loading remain limited.
- Subagent behavior is still limited/synthetic compared with a full child-agent runtime.
- CLI module execution from a source checkout requires editable install or `PYTHONPATH=src`; installed mode uses `lg-agent`.
