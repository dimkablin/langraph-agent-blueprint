# Security And Privacy Audit

Date: 2026-05-07

## Summary

Permission metadata, plugin path checks, MCP conservative defaults, and Langfuse redaction are good foundations. The highest-risk issue is unvalidated storage identifiers. The next tier is hardening around tool state access, network fetch behavior, plugin git timeouts, MCP config/process boundaries, and storage/config diagnostics.

## Findings

### P0: Session ID Path Traversal Can Escape The Session Namespace

- File: `src/langgraph_agent_blueprint/storage/session_storage.py:29`
- File: `src/langgraph_agent_blueprint/api/schemas.py:13`
- File: `src/langgraph_agent_blueprint/api/routes_sessions.py:14`
- Problem: `session_dir` joins `session_id` directly into a filesystem path. API accepts arbitrary `session_id` strings.
- Exploit scenario: A caller sends `session_id=../../../../audit_escape` or a Windows separator variant. Session creation/loading can create or read files outside the intended `sessions/<id>` namespace under or around storage.
- Why it matters: Session ids are external identifiers in API and CLI resume flows. They must not be path syntax.
- Suggested fix: Add a strict `SessionId`/`ThreadId` Pydantic type or helper accepting only generated-id shape such as `[A-Za-z0-9_-]{1,128}`. Resolve final session dir and require it to stay under the sessions root. Add API/schema/storage tests.

### P1: Tools Receive Mutable Whole-Graph State

- File: `src/langgraph_agent_blueprint/tools/base.py:40`
- File: `src/langgraph_agent_blueprint/services/tool_execution_service.py:34`
- Problem: `ToolExecutionContext.state` is the mutable graph state dict.
- Exploit scenario: A plugin/MCP-adapter-like future tool or a local custom tool mutates `context.state["permissions"]`, `pending_tool_calls`, or `metadata` directly during execution.
- Why it matters: Permission and state updates should pass through typed effects and graph reducers.
- Suggested fix: Pass a read-only snapshot or remove `state` entirely. Expose explicit fields and typed effect APIs only.

### P1: Web Fetch Has No SSRF/Scheme/Body Guardrails

- File: `src/langgraph_agent_blueprint/services/web_service.py:20`
- Problem: `httpx.Client(...).get(url)` follows redirects and materializes `response.text` without scheme/host policy or pre-truncation.
- Exploit scenario: With network enabled and approval, model/user can fetch internal services, metadata endpoints, local admin panels, or very large content.
- Why it matters: Permission approval is necessary but not sufficient for a production-style reference runtime.
- Suggested fix: Add URL validation, scheme allowlist (`http`, `https`), optional private-address denylist, max response bytes, content-type handling, and explicit docs for local-network fetch policy.

### P1: Plugin Git Install Has No Timeout

- File: `src/langgraph_agent_blueprint/services/plugin_service.py:388`
- Problem: `git` subprocess calls have no timeout.
- Exploit scenario: Network stalls, credentials prompt, or remote hang blocks the CLI indefinitely.
- Suggested fix: Use a timeout and return structured `PluginInstallResult(status="error")`.

### P1: MCP CWD Validation Is Existence-Only

- File: `src/langgraph_agent_blueprint/services/mcp_transport.py:174`
- Problem: `_validate_cwd` checks only that cwd exists and is a directory.
- Exploit scenario: An explicit config can start an MCP server in arbitrary local directories, potentially exposing files through that server.
- Why it matters: MCP server config is trusted local config, but the trust boundary should be documented and optionally enforce project-root confinement for untrusted servers.
- Suggested fix: Add policy: trusted servers may use arbitrary cwd, untrusted servers default to project-root confinement unless explicitly allowed.

### P1: API Approval Resume Does Not Preserve Session ID In Trace Context

- File: `src/langgraph_agent_blueprint/api/server.py:56`
- File: `src/langgraph_agent_blueprint/api/routes_chat.py:19`
- Problem: API resume calls `runtime.resume(thread_id, decision)` without `session_id`.
- Exploit scenario: Observability/privacy attribution can group approval traces under `thread_id` instead of the real session id.
- Suggested fix: Include `session_id` in approval request/response DTOs and pass it through, or resolve it from checkpoint state before opening the trace.

### P2: Permission Request Redaction Uses Exact Key Matching

- File: `src/langgraph_agent_blueprint/services/permission_service.py:96`
- Problem: Nested arg redaction redacts exact sensitive keys after lowercasing, while observability redacts substring matches.
- Exploit scenario: Keys such as `openai_api_key_extra` may not be redacted in permission display unless included as exact sensitive arg key.
- Suggested fix: Align permission redaction with observability's substring strategy or support both exact and substring matching.

### P2: Search Glob Can Return Absolute Paths

- File: `src/langgraph_agent_blueprint/services/search_service.py:22`
- Problem: `glob` returns absolute paths when root is absolute.
- Privacy impact: Tool output and session logs can contain local full paths.
- Suggested fix: Prefer project-relative display paths in tool content/metadata, keeping absolute paths internal.

### P2: Session Metadata Stores Full Project Root

- File: `src/langgraph_agent_blueprint/storage/session_storage.py:48`
- Problem: Session metadata stores the full project root.
- Privacy impact: Local session storage is expected to know project paths, but exported diagnostics or UI/API session listing can expose local path names.
- Suggested fix: Keep full path for local storage if needed, but expose redacted/basename/hash forms in remote/API outputs unless explicitly requested.

### P2: Broad Exception Swallowing In Destructors/Boundaries Can Hide Security-Relevant Cleanup Failures

- File: `src/langgraph_agent_blueprint/services/mcp_service.py:68`
- File: `src/langgraph_agent_blueprint/services/mcp_transport.py:107`
- Problem: Cleanup exceptions are ignored or only minimally handled.
- Why it matters: Process cleanup should be best-effort, but diagnostics should capture repeated failures.
- Suggested fix: Store cleanup warnings in diagnostics without crashing the graph.

## Positive Controls Observed

- File path traversal for file/search tools uses `resolve_under_root`.
- Plugin manifest-declared skill paths reject absolute/traversal paths.
- Plugin hooks are declarative and untrusted by default.
- MCP tools are external/high-risk and require permission by default.
- Langfuse disabled mode is no-op; no unscoped production `create_event` path was found.
- Langfuse path redaction is tested for Windows paths.
- Permission prompts redact default secret-like keys.

