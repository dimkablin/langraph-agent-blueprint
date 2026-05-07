# Technical Debt Fix Plan

Date: 2026-05-07

## Batch 1 Closed Items

Fixed on 2026-05-07:

- P0 storage/API runtime id validation and final session path confinement.
- P1 tool execution context no longer exposes mutable whole graph state.
- P1 `edit_file` rejects ambiguous multi-match snippets without changing files.
- P1 `web_fetch` has scheme, private-host, size, binary-content, redirect-final-url, and config guardrails.

## Batch 2 Closed Items

Fixed on 2026-05-07:

- P1 plugin policy activation is now a generic `PluginPolicyContribution` flow; Superpowers contributes a policy, and a fake plugin policy can activate a skill without graph-code changes.
- P1 `remember` durable writes moved out of `skill_router` into typed `SkillEffect` handling from `SkillInvocationService`.
- P1 dependency construction no longer starts MCP discovery; MCP tools register after explicit graph `/mcp`/chat registry loading or diagnostics discovery.
- P1 invalid MCP server configs are preserved in snapshot/diagnostics and shown by `/mcp` and `/doctor`.
- P1 plugin git install/update calls use `PLUGIN_GIT_TIMEOUT_SECONDS` and return structured timeout errors.
- P1 API approval/resume accepts and passes `session_id` so Langfuse resume traces stay grouped with the original session.
- P1 hook result application rebuilds touched nested metadata lists immutably.

| Priority | Area | Problem | Files | Suggested fix | Tests needed | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Storage/API | User-controlled session ids are path segments. | `storage/session_storage.py`, `api/schemas.py`, `api/routes_sessions.py`, `graph/builder.py` | Fixed in Batch 1: strict runtime id validation plus final-path confinement under session root. | Added storage/API traversal rejection tests for `../`, `..\\`, absolute paths, empty ids. | Medium: affects resume compatibility for hand-written ids. |
| P1 | Tool architecture | Tools receive mutable whole graph state. | `tools/base.py`, `services/tool_execution_service.py`, core/custom tool tests | Fixed in Batch 1: read-only/minimal context plus typed state effect applier. | Added malicious tool mutation regression test. | Medium: custom tools may depend on `context.state`. |
| P1 | Plugin policy | Superpowers policy is hardwired. | `graph/nodes/plugin_policy.py`, `plugins/superpowers.py`, `services/plugin_service.py` | Fixed in Batch 2: generic `PluginPolicyContribution` / `PluginPolicyContext` / `PluginPolicyResult` and declarative policy evaluator. | Added fake plugin policy, priority, disabled, error, and Superpowers acceptance tests. | Medium. |
| P1 | Skill effects | `remember` writes memory inside skill router by name. | `graph/nodes/skill_router.py`, `services/skill_service.py`, `skills/args.py` | Fixed in Batch 2: `SkillInvocationService` returns typed `SkillEffect`; controlled applier writes memory. | Added router source regression and unknown-skill no-memory-write test. | Medium. |
| P1 | File edit correctness | Ambiguous `old_text` edits are not rejected. | `services/file_service.py`, `tools/file_tools.py` | Fixed in Batch 1: require exactly one occurrence; occurrence selector remains future work. | Added multiple-match and missing-match edit tests. | Low. |
| P1 | MCP lifecycle | Dependency construction starts MCP servers. | `dependencies.py`, `services/mcp_service.py`, `graph/nodes/load_registries.py` | Fixed in Batch 2: dependency factory constructs `MCPService` only; explicit graph/command discovery registers MCP tools. | Added dependency no-discovery and graph load-registry discovery tests. | Medium. |
| P1 | MCP diagnostics | Invalid MCP config entries are silently skipped. | `services/mcp_service.py`, `commands/builtin.py` | Fixed in Batch 2: invalid server diagnostics are preserved and redacted. | Added malformed config `/doctor` and `/mcp` tests. | Low. |
| P1 | Network fetch | No URL/scheme/body policy. | `services/web_service.py`, `tools/web_tools.py` | Fixed in Batch 1: scheme allowlist, default private-host denylist, max bytes, binary handling, redirect-final-url validation. | Added scheme/private-host/local-opt-in/large-body/binary/redirect tests. | Medium: behavior change for local fetch smoke. |
| P1 | Plugin install | Git subprocesses have no timeout. | `services/plugin_service.py` | Fixed in Batch 2: configurable git timeout with phase-specific structured error. | Added fake hanging git timeout test. | Low. |
| P1 | API observability | Approval resume loses session id in root trace. | `api/schemas.py`, `api/server.py`, `api/routes_chat.py`, `graph/builder.py` | Fixed in Batch 2: approval DTO includes optional `session_id` and API routes pass it to `runtime.resume`. | Added API fake-Langfuse trace grouping regression. | Low/medium. |
| P1 | Hook state discipline | Hook applier shallow-copies metadata and may mutate nested lists. | `hooks/applier.py` | Fixed in Batch 2: touched nested lists/maps are rebuilt immutably. | Added hook applier input immutability tests. | Low. |
| P2 | Service size | Observability service is broad. | `services/observability_service.py` | Split redaction/mapper, factory/status, scoped turn. | Existing observability tests unchanged plus module-level unit tests. | Medium. |
| P2 | Service size | MCP service is broad. | `services/mcp_service.py` | Split config, discovery, invocation, diagnostics. | Existing MCP tests plus invalid config diagnostics. | Medium. |
| P2 | Service size | Plugin service is broad. | `services/plugin_service.py` | Split source install/cache from manifest adapters. | Existing plugin/Superpowers tests. | Medium. |
| P2 | Search correctness | Ripgrep errors return empty results. | `services/search_service.py`, `tools/search_tools.py` | Surface regex/rg failures as structured errors. | Invalid regex test returns tool error. | Low. |
| P2 | Event noise | Synthetic `model_token` events are generated after response. | `graph/nodes/model_call.py`, docs/UI renderer | Disable by default or mark as synthetic. | Stream-json remains valid; no unexpected token flood. | Low. |
| P2 | Session performance | Event dedupe scans full JSONL on each append. | `storage/session_storage.py` | Dedupe per turn before write or maintain index. | Long-session append benchmark/regression. | Low. |
| P2 | Session boundary | `list_sessions` bypasses `SessionMetadata` validation. | `storage/session_storage.py`, `services/session_service.py` | Validate list entries; report/skip corrupt metadata. | Corrupt metadata row does not break listing. | Low. |
| P2 | Privacy | Tool outputs expose absolute paths in glob/grep/file results. | `services/search_service.py`, `tools/file_tools.py`, docs | Prefer project-relative display paths; keep absolute only in internal metadata if required. | Windows and POSIX path display tests. | Medium. |
| P3 | Docs | README still presents old audited Claude Code-like source context as current narrative. | `README.md` | Move historical migration material to a historical section or docs link. | Docs consistency test for current README claims. | Low. |
| P3 | Config docs | `.env.example` omits `MCP_CONFIG_JSON` and `LG_AGENT_MCP_CONFIG_JSON`. | `.env.example`, `docs/MCP.md` | Add commented MCP JSON examples. | Env loading test already exists; add docs grep if desired. | Low. |
| P3 | Packaging smoke | `python -m langgraph_agent_blueprint` requires install or `PYTHONPATH=src`. | README, packaging docs | Document source-tree usage or require editable install before smoke. | CLI smoke test can run with `PYTHONPATH=src`. | Low. |
| P3 | Encoding | `cli.py` has UTF-8 BOM. | `src/langgraph_agent_blueprint/cli.py` | Remove BOM in formatting-only cleanup. | AST parse with `encoding="utf-8"` succeeds. | Low. |
| P3 | Test readability | Cyrillic chat test strings are mojibake. | `tests/test_observability_cli.py` | Replace with correct UTF-8 or ASCII. | Existing test remains green. | Low. |
