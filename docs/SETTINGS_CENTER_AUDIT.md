# Settings Center Audit

Audit date: 2026-05-09

This is an audit-only pass for a future frontend Settings Center. No production code, frontend code, tests, or API routes were changed as part of this audit.

## Baseline

The working tree was already dirty before this audit due to existing frontend changes. The audit did not modify those files.

Baseline commands:

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short` | dirty before audit | Existing frontend changes were present. Git also printed a global ignore permission warning for `C:\Users\dimka/.config/git/ignore`. |
| `python -m pytest -q` | passed | Full backend test suite passed. |
| `npm.cmd --prefix frontend run test` | passed after rerun | First sandboxed run failed with `spawn EPERM`; rerun with normal approved execution passed. |
| `npm.cmd --prefix frontend run test:static` | passed | Static frontend contract tests passed. |
| `npm.cmd --prefix frontend run build` | passed | Vite production build passed. |
| `$env:PYTHONPATH="src"; python -m langgraph_agent_blueprint eval run --all` | passed | All eval scenarios passed. Reports were written under ignored `.eval_runs/`. |

## Current Frontend Settings Surface

The frontend currently has a lightweight right-side settings drawer opened from the sidebar. It renders `RuntimeStatusPanel`, which is read-only and displays aggregate status counts:

- plugins count
- hooks count
- MCP server count
- config validation status
- observability mode

Current frontend status data comes from `frontend/src/api/status.ts`, which calls:

- `GET /plugins`
- `GET /hooks`
- `GET /config`
- `GET /config/validate`
- `GET /observability`
- `GET /mcp`

The frontend does not currently expose editable settings, config patching, plugin enable/disable, skill enable/disable, hook enable/disable, or MCP server enable/disable.

## Current Backend Settings Surface

The backend currently supports read-only diagnostics for configuration and runtime extension status.

Existing frontend-facing endpoints:

- `GET /config`
- `GET /config/explain`
- `GET /config/validate`
- `GET /plugins`
- `GET /hooks`
- `GET /mcp`
- `GET /observability`
- `GET /skills`
- `GET /tools`
- `GET /commands`

Important caveat: `GET /mcp` calls `MCPService.discover()`. This can start configured stdio MCP processes. A Settings Center should treat that as an explicit discovery action or use a future snapshot-only endpoint.

## Config Loading

`AppConfig` has explicit layered loading:

```text
CLI explicit args / programmatic overrides
> process environment variables
> project config
> user config
> project-root .env
> defaults
```

Project config is `.lg-agent/config.toml`, with `langgraph-agent.toml` as compatibility fallback. User config is `%APPDATA%/langgraph-agent-blueprint/config.toml` on Windows or `~/.config/langgraph-agent-blueprint/config.toml` elsewhere.

Secrets are redacted in config show/explain outputs. Token budget fields such as `context_max_tokens` are intentionally not redacted.

## Current AppConfig Fields

Core runtime:

- `llm_provider`
- `model_name`
- `storage_dir`
- `project_root`
- `cwd`
- `permission_mode`
- `network_enabled`
- `cors_allowed_origins`

Provider-specific:

- `anthropic_api_key`
- `anthropic_model`
- `openai_api_key`
- `openai_model`
- `ollama_base_url`
- `ollama_model`
- `openai_compatible_base_url`
- `openai_compatible_api_key`
- `openai_compatible_model`

Web and context:

- `web_fetch_allow_private_hosts`
- `web_fetch_max_bytes`
- `context_max_tokens`
- `context_max_file_bytes`
- `context_max_directory_files`
- `context_max_glob_files`

Tools and compaction:

- `shell_timeout_seconds`
- `tool_output_limit`
- `auto_compact_threshold`
- `max_recent_messages_after_compact`

Extensions:

- `skills_paths`
- `plugin_paths`
- `plugin_git_timeout_seconds`
- `mcp_config`
- `langfuse`

## Missing LLM Runtime Preferences

The current runtime does not have typed config fields or API DTOs for common generation controls:

- `temperature`
- `max_output_tokens`
- `top_p`
- provider request timeout/retry policy
- provider-specific tool calling mode
- per-session provider/model override

The frontend currently has `model_intelligence` in `ChatRequest`, but this is not the same as provider-level generation parameters. It is run metadata, not a stable model config contract.

## Category Findings

### LLM

Current support:

- provider/model are configured through `AppConfig`
- API keys are env/config values and are redacted
- effective model is exposed indirectly in session metadata and config show
- frontend can choose `model_intelligence` per chat request

Gaps:

- no editable typed settings for temperature, max output tokens, top_p, timeout, retry, or model list
- no endpoint for provider capabilities or available models
- no safe config patch endpoint

Recommendation:

- MVP Settings Center should show provider/model/API-key presence read-only.
- Add editable generation parameters only after backend owns typed `ModelSettings` and provider capability validation.

### Permissions

Current support:

- `permission_mode` is configured in `AppConfig`
- runtime emits typed permission events
- approval/rejection uses typed API DTOs

Recommendation:

- Show permission mode read-only in MVP.
- Changing permission mode from browser should be deferred or require a typed config patch with explicit confirmation.

### Web and Network

Current support:

- `network_enabled`
- `web_fetch_allow_private_hosts`
- `web_fetch_max_bytes`
- web fetch guardrails enforce scheme/private-host limits

Recommendation:

- Show status read-only in MVP.
- `web_fetch_allow_private_hosts` is dangerous and should not be a casual toggle. If ever exposed, require explicit confirmation and write through validated project config.

### Context

Current support:

- `context_max_tokens`
- `context_max_file_bytes`
- `context_max_directory_files`
- `context_max_glob_files`
- session context state endpoint
- context events and budget reports

Recommendation:

- Show context budget values and current session context read-only in MVP.
- Editing budgets is safe only as a project-level config patch after validation. Per-session override can be added later.

### Plugins

Current support:

- plugin discovery from configured paths/cache
- manifest `enabled`
- contribution counts and diagnostics through `/plugins`
- trust metadata
- plugin install/update/remove exist in service/CLI, not frontend API

Recommendation:

- Show plugins read-only in MVP.
- Enable/disable should be a project config patch, not an in-memory frontend decision.
- Install/update/remove should remain deferred until trust UX and provenance display are designed.

### Skills

Current support:

- built-in, file-based, and plugin skills
- `SkillMetadata.enabled` exists in skill files
- disabled skills are tracked by registry
- `GET /skills` lists currently enabled skills

Gaps:

- no API to list disabled skills separately in a stable DTO
- no API/config patch for skill enable/disable

Recommendation:

- Show skill registry read-only in MVP.
- Skill enable/disable should be config-file or project patch driven.

### Hooks

Current support:

- typed hook contributions
- `enabled` and priority fields exist on hook contributions
- `/hooks` exposes registered hooks read-only

Recommendation:

- Show hooks read-only in MVP.
- Enable/disable hook can be safe later, but must be implemented as a typed config patch because hooks affect prompts and control flow.

### MCP

Current support:

- configured MCP servers
- enabled flag on server config
- invalid config diagnostics
- discovery of tools/resources/prompts
- redacted server config helper exists in service

Risks:

- `/mcp` starts discovery and may spawn stdio processes.
- editing command/args/cwd from browser is high risk.

Recommendation:

- Add snapshot-only MCP status before using Settings Center auto-refresh.
- Enable/disable server can be a confirmed config patch later.
- Editing command/args/cwd should stay config-file only for now.

### Observability

Current support:

- `LANGFUSE_ENABLED`
- key presence, base URL status, environment/release
- capture inputs/outputs
- include project paths
- runtime events mode
- `/observability` redacts secrets

Recommendation:

- Show observability status read-only in MVP.
- Runtime events mode and capture flags can become safe editable settings after typed config patch support.
- API keys and base URL should remain env/config-file only in MVP.

### Sessions

Current support:

- session IDs, thread IDs, typed session list/detail/context/child-run endpoints
- storage/export paths

Recommendation:

- Settings Center can show current session/thread/project status read-only.
- Session management belongs in session UI, not global settings.

### Eval

Current support:

- CLI eval/replay harness
- no API dashboard endpoints

Recommendation:

- Keep eval UI out of Settings Center MVP.

### UI-only Preferences

Safe browser-only preferences:

- theme
- density
- event verbosity
- show debug events
- auto-scroll
- sidebar visibility
- locale/language

Recommendation:

- Store UI-only preferences in local storage or frontend app state. They should not write backend config.

## Security Findings

Settings Center must not:

- show or edit API keys in the browser
- write arbitrary config files without typed validation
- let the frontend mutate plugin/skill/hook/MCP runtime objects directly
- enable private-host web fetch without explicit warning
- edit MCP server command/args/cwd from browser MVP
- install/update/remove plugins without trust/provenance UX
- expose absolute project paths unless explicitly configured
- send full config or secrets to Langfuse/event payloads

All mutable runtime settings should go through typed backend DTOs, validation, diagnostics, and an auditable event/log path.

## Readiness Summary

Settings Center can start as a read-only center plus UI-only preferences.

Backend needs new typed settings API before safe editing:

- settings snapshot/schema DTOs
- typed config patch model
- validation-before-save
- project-config write policy
- confirmation flags for dangerous changes
- audit/runtime events for accepted changes

