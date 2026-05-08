# Context Providers And Attachments

Phase 6 adds a typed runtime layer for local and external context. Context is resolved by graph-owned provider services before `context_builder`; providers do not call models and do not execute tools directly from CLI/API.

## Supported References

CLI chat, headless query, and API chat requests can attach context through:

```text
@README.md
@src/
@glob:src/**/*.py
@notebook:notebook.ipynb
@mcp:server:mcp://server/resource
@plugin:example_plugin:reference
@url:https://example.com
@"path with spaces/file.txt"
```

Plain email addresses and ordinary `@username` mentions are ignored by the conservative parser. User text stays in the prompt; parsed references are extra typed metadata.

## Providers

- `file`: reads text files under the project root with max-byte limits and project-relative titles.
- `directory`: lists a bounded directory tree summary and does not dump file contents.
- `glob`: returns a bounded file-list summary and does not dump file contents.
- `notebook`: reads notebook JSON safely and summarizes cells without execution.
- `mcp_resource`: reads configured MCP resources through `MCPService` and marks them `mcp_external`.
- `plugin`: resolves declarative plugin context providers and marks them `plugin_provided`.
- `url`: uses `WebService.fetch`, so network config, scheme checks, private-host policy, redirect validation, response caps, and permission policy still apply.
- `text`: supports pasted text/API text attachments.
- `image` and `pdf`: store metadata and emit safe placeholder summaries in this MVP; OCR, image understanding, and full PDF extraction are future work.

## Budget

`ContextBudgetService` uses a cheap character-based token estimate and applies a per-turn budget before fragments enter system context. Defaults are:

```text
CONTEXT_MAX_TOKENS=8000
CONTEXT_MAX_FILE_BYTES=200000
CONTEXT_MAX_DIRECTORY_FILES=200
CONTEXT_MAX_GLOB_FILES=100
```

The graph stores a JSON-safe `ContextBudgetReport` with included, truncated, and dropped fragments.

## Trust And Prompt Injection

Every fragment carries a trust marker:

- `trusted_local`
- `user_provided`
- `untrusted_external`
- `mcp_external`
- `plugin_provided`

Rendered context explicitly says attached content is data, not instructions. External, MCP, plugin, and user-provided context receives a prompt-injection warning. Local file content is still context, not instruction, unless the user explicitly says otherwise.

## Security

File, directory, glob, and notebook providers stay under the project root. Path traversal and outside-root absolute paths are rejected with structured context errors. URL context reuses `web_fetch` guardrails and does not fetch private/internal hosts unless `WEB_FETCH_ALLOW_PRIVATE_HOSTS=true`. Context events and observability payloads avoid full local paths by default and do not include huge raw content.

## Graph Integration

The main graph now routes prompt/model and skill flows through:

```text
normalize_input -> command_router/plugin_policy/skill_graph -> resolve_context -> context_builder
```

`resolve_context` emits `context_resolution_started`, `context_fragment_added`, `context_resolution_error`, and `context_budget_applied` events. `context_builder` consumes rendered, budgeted fragments, not raw paths.

## Persistence And Commands

Session metadata stores context references, attachment metadata, and the budget report. Large content is kept out of top-level metadata; resolved fragments remain bounded by the context budget. `/context` shows current references, fragments, budget usage, and resolution errors.

## Subagents

`SubagentRequest.inherit_context` defaults to `true`. Child graphs receive deep-copied context references/fragments/budget metadata so parent and child states do not share mutable containers. Large attachments are not blindly expanded beyond the already-budgeted fragments.

## Current Limitations

- Image/PDF attachments are metadata placeholders only.
- Directory and glob providers summarize file lists rather than reading every file.
- MCP resource context requires explicit MCP configuration and discovery.
- URL context requires enabled network config and normal permission/guardrail behavior.
- A future frontend can build richer attachment UX on top of these typed DTOs.
