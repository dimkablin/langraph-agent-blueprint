# Final Reference-Ready Acceptance

Date: 2026-05-09

This is the final acceptance audit for the LangGraph Agent Blueprint backend/runtime/API/frontend reference implementation. The audit did not intentionally change production code or tests; it created this acceptance document only. The current workspace already contains uncommitted code/test changes outside this audit document, listed under "Cleanliness".

## Summary

| Area | Result | Notes |
| --- | --- | --- |
| Backend tests | pass | `python -m pytest -q` passed. |
| Frontend tests | pass with sandbox caveat | Normal sandbox run hit Node `spawn EPERM`; rerun outside sandbox passed. |
| Frontend static checks | pass | `npm.cmd --prefix frontend run test:static` passed. |
| Frontend build | pass with sandbox caveat | Normal sandbox run hit Vite `spawn EPERM`; rerun outside sandbox passed. |
| Eval/replay | pass | Both module invocation and installed CLI invocation passed all scenarios. |
| Editable install | pass with environment changes | User install succeeded after elevated rerun; `lg-agent.exe` installed outside PATH. |
| CLI quickstart | partial | Most commands pass; `lg-agent query "hello"` can fail on Windows CP1251 when output contains Unicode. |
| API quickstart | pass with local port caveat | `serve` works on a free port; port `8000` was already occupied in this environment. |
| Frontend dev server | pass | Vite dev server served HTML with root node. |
| Security smoke | pass with warnings | Redaction, permission rejection, no direct frontend tool execution, and MCP snapshot behavior validated. |
| Docs consistency | pass with historical-doc caveat | Current docs contain intentional future limitations; older audit docs still contain historical stale findings. |
| Release cleanliness | partial | Ignored artifacts exist as expected; worktree has uncommitted code/test changes outside this audit doc. |

## Commands Run

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short` | pass | Initial status printed only the external global ignore permission warning. Later status showed uncommitted code/test changes. |
| `python -m pytest -q` | pass | Full Python suite passed. |
| `npm.cmd --prefix frontend run test` | pass after rerun | Sandbox run failed with `spawn EPERM`; elevated rerun passed 18 tests. |
| `npm.cmd --prefix frontend run test:static` | pass | Static frontend contract checks passed. |
| `npm.cmd --prefix frontend run build` | pass after rerun | Sandbox run failed with `spawn EPERM`; elevated rerun built successfully. |
| `$env:PYTHONPATH="src"; python -m langgraph_agent_blueprint eval run --all` | pass | All eval scenarios passed. |
| `python -m pip install -e ".[test,api,openai,ollama,observability]"` | pass after rerun | First run failed with Temp permission; elevated rerun succeeded and installed `lg-agent.exe` outside PATH. |
| `lg-agent --help` | pass via full path | Plain `lg-agent` is not available until `C:\Users\dimka\AppData\Roaming\Python\Python314\Scripts` is added to PATH. |
| `lg-agent doctor` | pass via full path | Status `ok`; Langfuse SDK installed and configured in this environment. |
| `lg-agent config validate` | pass via full path | Config loaded successfully. |
| `lg-agent eval run --all` | pass via full path | All eval scenarios passed. |
| `lg-agent query "hello"` | fail under default shell | Runtime produced an answer, but Rich output failed with `UnicodeEncodeError` on CP1251 for `→`; workaround `PYTHONIOENCODING=utf-8` passed. |
| `lg-agent tools list` | pass via full path | Core tools listed. |
| `lg-agent skills list` | pass via full path | Built-in and Superpowers skills listed. |
| `lg-agent plugins list` | pass via full path | Superpowers plugin listed from `.storage`. |
| `lg-agent config explain` | pass via full path | Secrets redacted; context token budget visible. |
| `lg-agent eval run basic-chat` | pass via full path | Scenario passed. |
| `lg-agent chat` | not launched interactively | `lg-agent chat --help` passed; interactive REPL was not run to avoid blocking the audit. |
| `lg-agent serve --host 127.0.0.1 --port 8000` | local port occupied | A server was already responding on `8000`; a new process could not bind. Same command pattern worked on port `8765`. |
| `GET /openapi.json` | pass | 23 OpenAPI paths observed on smoke server. |
| `GET /config` | pass | Typed config endpoint returned successfully. |
| `GET /mcp/snapshot` | pass | Passive snapshot endpoint returned successfully. |
| `POST /chat` | pass | Returned session id and runtime events. |
| `POST /chat/stream` | pass | SSE response included `done` and final response frames. |
| `POST /approval` | pass | Typed rejection preserved session id, emitted `permission_resolved`, and did not write the file. |
| `npm.cmd --prefix frontend run dev` | pass | Dev server served HTML with a root node. |

## Install Notes

Editable install succeeded after an elevated rerun. It installed optional observability dependencies and changed the user Python environment:

- installed `langgraph-agent-blueprint-0.1.0` editable
- installed `langfuse-4.6.1`
- installed OpenTelemetry packages
- changed `protobuf` from `7.34.1` to `6.33.6`
- changed `importlib_metadata` from `9.0.0` to `8.7.1`
- installed `lg-agent.exe` under `C:\Users\dimka\AppData\Roaming\Python\Python314\Scripts`, which is not on PATH

This is acceptable for the install check, but README quickstart should mention adding the user Scripts directory to PATH or using `python -m langgraph_agent_blueprint`.

## CLI Smoke

The CLI surface is functionally present:

- `--help` shows query, serve, chat, sessions, skills, tools, plugins, eval, and config commands.
- `doctor` reports status `ok`.
- `config validate` passes.
- `tools list`, `skills list`, `plugins list`, `config explain`, and `eval run basic-chat` pass.
- `eval run --all` passes.

Known blocker:

- `lg-agent query "hello"` can fail on Windows default CP1251 output when the model response contains Unicode such as `→`.
- The command succeeds when `PYTHONIOENCODING=utf-8` is set.
- This is a reference-readiness issue for Windows CLI quickstart because the runtime completes but final console rendering crashes.

## API Smoke

`lg-agent serve` works on a free local port. In this workspace, port `8000` was already occupied, so a new `serve --port 8000` process failed to bind. The same command pattern on port `8765` passed:

- `GET /openapi.json`: 200
- `GET /config`: 200
- `GET /mcp/snapshot`: 200
- `POST /chat`: 200 with session id and events
- `POST /chat/stream`: 200 with SSE done/final response
- `POST /approval`: 200 with typed rejection and no write side effect

Observed non-blocking warning:

- During stream smoke with Langfuse/OpenTelemetry enabled, stderr included `Failed to detach context` from OpenTelemetry context cleanup. The API response still succeeded. Treat as P1 observability polish before external release.

## Frontend Smoke

Automated smoke:

- `npm.cmd --prefix frontend run test` passed outside sandbox.
- `npm.cmd --prefix frontend run test:static` passed.
- `npm.cmd --prefix frontend run build` passed outside sandbox.
- `npm.cmd --prefix frontend run dev` served HTML from `http://127.0.0.1:5173/`.

Manual browser smoke was not performed in this audit pass. The covered automated checks validate the TypeScript entrypoint, API/reducer separation, graph-facing endpoints, SSE parser, reducer behavior, settings center contract, composer suggestions, sidebar timestamps, and static no-Luxms/no-direct-tool constraints.

## Docs Consistency

Focused scan of current docs:

```powershell
rg -n "claude-code-langraph|claude_code_langgraph|claude-code-langgraph|claude-like-project|broken|partially_working|registered_but_unreachable|TODO|not implemented|unsupported" README.md frontend/README.md docs/FRONTEND_IMPLEMENTATION_PLAN.md docs/CONFIG.md docs/PLUGIN_SDK.md docs/MCP.md docs/OBSERVABILITY.md docs/SETTINGS_CENTER_AUDIT.md docs/SETTINGS_FRONTEND_PLAN.md docs/SETTINGS_API_CONTRACT_PLAN.md docs/SETTINGS_OPTION_MATRIX.md docs/EVAL_REPLAY.md
```

Current-doc hits are acceptable:

- README mentions the historical source path and the old missing `claude-like-project` path as audit provenance.
- README and MCP docs state intentional future limitations: Streamable HTTP, OAuth, MCP server mode, prompt-to-skill registration, and plugin marketplace install/update are not implemented.

Whole-doc scan still finds old audit documents with stale historical statuses. Examples:

- `docs/TOOLS_RUNTIME_AUDIT.md` still says `agent` was limited/synthetic.
- `docs/MCP_RUNTIME_AUDIT.md` still says `/mcp` was unsupported by CommandRegistry.

These are historical audit artifacts, not current source-of-truth docs, but they should be archived or marked historical more loudly before public release.

## Artifact And Cleanliness Check

Tracked artifact check:

- No tracked `.storage/`, `.eval_runs/`, `test_runs/`, `node_modules/`, `dist/`, `.env`, or `config/` files were found.

Ignored local artifacts exist:

- `.env`
- `.storage/`
- `.eval_runs/`
- `test_runs/`
- `frontend/node_modules/`
- `frontend/dist/`
- `config/`

These are ignored by `.gitignore`. `test_runs/` contains long nested paths that cause Git status warnings when using `--ignored`; it is ignored and should remain untracked.

Current worktree caveat:

- `src/langgraph_agent_blueprint/api/serializers.py` is modified.
- `tests/test_api_streaming.py` is modified.

Those changes were not made by this acceptance audit. Tests passed with them present. The workspace is not tag-clean until those changes are either committed or reverted by the owner.

## Security Smoke

| Check | Result | Evidence |
| --- | --- | --- |
| `/config` redacts secrets | pass | TestClient smoke with fake secret values confirmed no raw key values in `/config` or `/config/explain`; `***` redaction present. |
| Settings Center does not render secret values | pass | Frontend static settings tests pass; UI renders key presence, not values. |
| `/mcp/snapshot` does not start MCP processes | pass | Backend test `test_mcp_snapshot_does_not_start_stdio_discovery` passes; Settings uses `/mcp/snapshot`, not `/mcp`. |
| Plugin install requires network enabled | pass | `PluginService.install` gates git install behind `NETWORK_ENABLED=true`; docs and tests cover this path. |
| `web_fetch` blocks private hosts by default | pass | Config defaults disable network/private hosts; tests cover private-host flag and guardrails. |
| Session id traversal | pass | Session/storage/API tests cover invalid `session_id` and `thread_id`. |
| No old Luxms endpoints in main frontend | pass | Static frontend test covers no Luxms/auth old endpoints. |
| Frontend does not call direct tool execution endpoints | pass | Static frontend test and source scan show graph-facing endpoints only. |
| Approval rejection avoids side effect | pass | API smoke rejected `write_file`; target file was not created. |

## Remaining Limitations

Blocking before a clean public v0.1 tag:

1. Resolve or document the Windows CLI Unicode output failure for `lg-agent query` under CP1251.
2. Resolve the current uncommitted `api/serializers.py` and `tests/test_api_streaming.py` changes so the release/tag worktree is clean.

Recommended P1 polish:

1. Investigate OpenTelemetry `Failed to detach context` stderr during API stream smoke with Langfuse enabled.
2. Add README note for user Scripts PATH after `pip install --user`.
3. Add README note that `PYTHONIOENCODING=utf-8` or UTF-8 terminal mode may be needed on legacy Windows consoles until the CLI renderer is hardened.
4. Archive or clearly label older audit docs that contain stale pre-fix statuses.
5. Add an automated browser smoke with fake provider for the frontend once Playwright/browser infrastructure is available.

Known future/non-MVP work remains intentionally out of scope:

- MCP server mode
- MCP Streamable HTTP/OAuth
- IDE/LSP integration
- background tasks
- plugin marketplace/install UI
- settings mutation API
- eval dashboard
- full attachment upload/OCR/vision

## Readiness Score

Reference readiness score: **8.5 / 10**.

The runtime, API contract, frontend MVP, settings center, and eval harness are strong enough for an internal reference-ready candidate. However, the current workspace should not be tagged as a clean public `v0.1` until the Windows CLI Unicode quickstart failure and uncommitted worktree caveat are resolved.

Recommendation: mark as **`v0.1 reference-ready candidate`** now, then apply the small polish list before a durable release tag.
