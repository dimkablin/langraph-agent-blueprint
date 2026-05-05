# Fix Implementation Log

Date: 2026-05-06

Scope: implementation pass after the runtime audit. This pass fixed the P0/P1 blockers that prevented tools, skills, commands, events, permissions, sessions, and Ollama tool calling from working end-to-end.

## P0 Fixed

| Issue | Status | Files changed | Tests |
| --- | --- | --- | --- |
| State list fields overwrote events/results | fixed | `graph/state.py`, `models/messages.py`, node event returns | `tests/runtime_audit/test_runtime_blockers.py` |
| Provider ignored `system_context` and tools | fixed | `services/model_provider.py`, `graph/nodes/model_call.py` | `tests/runtime_audit/test_provider_tool_binding.py` |
| Tool result was not returned as `ToolMessage` | fixed | `graph/nodes/model_call.py`, `graph/nodes/tool_executor.py`, `graph/nodes/tool_router.py`, `graph/nodes/permission_gate.py`, `utils/serialization.py` | `tests/runtime_audit/test_runtime_blockers.py` |
| `project_root` defaulted to `storage_dir` | fixed | `dependencies.py`, tests updated to pass explicit workspace where needed | `tests/runtime_audit/test_runtime_blockers.py` |
| Permission decisions/events were lost | fixed | `graph/state.py`, `graph/nodes/permission_gate.py`, `graph/nodes/persist_session.py`, `storage/session_storage.py` | `tests/runtime_audit/test_runtime_blockers.py`, `tests/runtime_audit/test_tools_e2e.py` |
| Skills were prompt-only and scope was unenforced | fixed with documented limits | `graph/nodes/skill_router.py`, `graph/nodes/tool_router.py`, `graph/nodes/model_call.py` | `tests/runtime_audit/test_skills_e2e_runtime.py` |

## P1 Fixed

| Issue | Status | Files changed | Tests |
| --- | --- | --- | --- |
| `/compact` fell through to model | fixed | `graph/routing.py`, `graph/builder.py`, `graph/nodes/compact_context.py` | `tests/runtime_audit/test_commands_e2e.py` |
| `/export` was a placeholder | fixed | `graph/nodes/command_router.py` | `tests/runtime_audit/test_commands_e2e.py` |
| `/resume` did not restore state | fixed | `graph/nodes/command_router.py`, `graph/builder.py`, `storage/session_storage.py` | `tests/runtime_audit/test_commands_e2e.py` |
| `/doctor` was a placeholder | fixed | `commands/builtin.py`, `graph/nodes/command_router.py` | `tests/runtime_audit/test_commands_e2e.py` |
| `/skills`, `/status`, `/cost`, `/config`, `/memory`, `/todo` were too shallow | fixed | `commands/builtin.py`, `graph/nodes/load_registries.py`, `graph/nodes/command_router.py` | `tests/runtime_audit/test_commands_e2e.py` |
| `grep` broke on Windows absolute paths | fixed | `services/search_service.py` | `tests/runtime_audit/test_runtime_blockers.py` |
| fake provider misparsed JSON `write_file` args | fixed | `services/model_provider.py` | `tests/runtime_audit/test_tools_e2e.py` |
| PowerShell ran through `cmd.exe` on Windows | fixed | `services/shell_service.py` | `tests/runtime_audit/test_tools_e2e.py` |
| `web_search` returned empty success without provider | fixed | `services/web_service.py` | `tests/runtime_audit/test_tools_e2e.py` |
| stream-json returned only final surviving events | fixed | `graph/builder.py`, `cli.py` | `tests/test_cli_headless.py` |
| session metadata was overwritten by event/tool append calls | fixed | `storage/session_storage.py`, `graph/builder.py` | `tests/runtime_audit/test_tools_e2e.py`, `tests/runtime_audit/test_commands_e2e.py` |

## Xfail Conversion

`tests/runtime_audit/test_runtime_blockers.py` no longer uses `xfail`. The former blockers now pass as normal regression tests.

## Added Tests

- `tests/runtime_audit/test_provider_tool_binding.py`
- `tests/runtime_audit/test_tools_e2e.py`
- `tests/runtime_audit/test_commands_e2e.py`
- `tests/runtime_audit/test_skills_e2e_runtime.py`
- New stream-json coverage in `tests/test_cli_headless.py`
- Updated permission/project-root coverage in `tests/test_permission_interrupts.py`

## Manual Runtime Checks

Workspace: `test_runs/runtime-smoke-workspace-2`.

Passed:

- simple fake chat
- `/help`, `/skills`, `/status`, `/config`
- `read_file`
- `write_file` with approval/resume
- `edit_file` after persisted prior read with approval/resume
- `glob`, `grep`
- `bash` with approval/resume
- `todo_write`, then `/todo` in a later turn
- `/skill remember`, then `/memory`
- `/skill verify` events
- `/compact`
- `/export`
- `/resume`
- stream-json event flow
- Ollama `qwen3:14b` normal chat
- Ollama `qwen3:14b` native `read_file` tool call through graph

Ollama evidence:

```text
ollama_tool_read_file: OK The exact first line of README.md is: OLLAMA_SMOKE_LINE
```

## Verification

```text
python -m pytest
69 passed in 61.44s

npm.cmd --prefix frontend run test:static
3 static checks passed

npm.cmd --prefix frontend run build
vite build passed outside sandbox after sandbox spawn EPERM
```

## Remaining Limitations

- Skills now run through graph routing, emit lifecycle events, enforce allowed tools, and can use the normal model/tool loop. Most bundled skills remain prompt-driven capabilities rather than hardcoded deterministic workflows. `remember` has a direct durable memory path.
- `web_fetch` is disabled unless `NETWORK_ENABLED=true` and still requires permission.
- `web_search` is unavailable unless a real search provider is configured.
- MCP and plugins remain conservative/minimal integrations; no full external server/plugin marketplace lifecycle is claimed.
- `agent` still has limited synthetic subagent behavior unless expanded in a later P2 pass.
