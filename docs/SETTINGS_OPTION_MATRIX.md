# Settings Option Matrix

Audit date: 2026-05-09

Classification values:

- Frontend editable: `yes`, `read_only`, `dangerous_requires_confirmation`, `config_file_only`, `env_only`, `future`, `not_recommended`
- Scope: `global`, `project`, `session`, `run`, `ui_only`, `plugin`, `mcp_server`
- Priority: `MVP`, `P1`, `P2`, `future`, `not_recommended`

| Setting | Category | Current source | Current backend support | Frontend editable? | Scope | Requires restart? | Security risk | API needed | Priority | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Provider | LLM | `llm_provider` | AppConfig, config diagnostics | read_only | project | yes for running runtime | medium | `GET /settings` later | MVP | Show current provider first. Switching provider needs capability validation. |
| Model name | LLM | `model_name`, provider-specific model envs | AppConfig, effective model | read_only | project | yes for running runtime | low | `GET /settings` later | MVP | Editable later after model capability contract exists. |
| API key presence | LLM | env, `.env`, config | redacted config and observability status | read_only | project | maybe | high | none | MVP | Show only present/missing. Never render key value. |
| API keys | LLM | env, `.env` | accepted by AppConfig | env_only | project | yes | high | none | not_recommended | Do not edit in browser MVP. |
| Provider base URL | LLM | provider-specific config | AppConfig | config_file_only | project | yes | high | future validated patch | P2 | Can expose internal hosts; keep read-only initially. |
| Temperature | LLM | not present | missing | future | session/run | no if implemented per request | low | `ModelSettings` and `PATCH /settings` or `ChatRequest.model_settings` | P1 | Needs provider support and validation. |
| Max output tokens | LLM | not present | missing | future | session/run | no if implemented per request | low | same as above | P1 | Distinct from context budget. |
| Top P | LLM | not present | missing | future | session/run | no | low | same as above | P2 | Provider-specific support varies. |
| Tool calling mode | LLM | not present | missing | future | session/run | no | medium | provider capability schema | P2 | Do not expose until provider semantics are stable. |
| Streaming enabled | Runtime | API path choice | SSE endpoint exists | yes | ui_only/run | no | low | none for UI-only | MVP | UI can choose stream vs non-stream if fallback remains. |
| Model intelligence | Runtime | `ChatRequest.model_intelligence` | run metadata accepted | yes | run | no | low | existing `/chat` | MVP | Already in composer; keep as run preference, not config. |
| Permission mode | Permissions | `permission_mode` | AppConfig | read_only | project | yes | high | future settings patch | MVP | Changing this changes safety posture. |
| Read-only bypass behavior | Permissions | `permission_mode` | AppConfig modes | read_only | project | yes | high | future settings patch | P1 | Explain behavior, do not casual-toggle. |
| Shell approval behavior | Permissions | tool metadata and mode | runtime permission flow | read_only | project | yes | high | future policy config | P2 | Not a standalone config today. |
| Network enabled | Network | `NETWORK_ENABLED` | AppConfig | read_only | project | yes | high | future settings patch | MVP | Enables git plugin install and external network paths. |
| Web fetch private hosts | Network | `WEB_FETCH_ALLOW_PRIVATE_HOSTS` | AppConfig/web guardrails | dangerous_requires_confirmation | project | yes | high | typed patch with confirmation | P2 | Must show SSRF/local-network warning. |
| Web fetch max bytes | Network | `WEB_FETCH_MAX_BYTES` | AppConfig | future | project | yes | medium | typed patch | P2 | Safe with upper/lower bounds. |
| Context max tokens | Context | `CONTEXT_MAX_TOKENS` | AppConfig/context budget | read_only | project | yes | low | future typed patch | MVP | Already surfaced in composer meter. |
| Context max file bytes | Context | `CONTEXT_MAX_FILE_BYTES` | AppConfig/provider service | read_only | project | yes | medium | future typed patch | P1 | Needs bounds to avoid huge prompt payloads. |
| Context max directory files | Context | `CONTEXT_MAX_DIRECTORY_FILES` | AppConfig | read_only | project | yes | low | future typed patch | P1 | Good later UI setting. |
| Context max glob files | Context | `CONTEXT_MAX_GLOB_FILES` | AppConfig | read_only | project | yes | low | future typed patch | P1 | Good later UI setting. |
| Trust markers explanation | Context | runtime docs/events | supported | yes | ui_only | no | low | none | MVP | UI copy/help only. |
| Plugin paths | Plugins | `PLUGIN_PATHS` | AppConfig/PluginService | config_file_only | project | yes | high | future config patch maybe | P2 | Paths can expose local filesystem. |
| Plugin enabled | Plugins | manifest `enabled` | discover respects enabled | future | plugin | yes/reload | medium | `PATCH /plugins/{name}/enabled` via config policy | P1 | Needs design: manifest edit vs project override. |
| Plugin trust level | Plugins | manifest trust | Plugin DTOs | read_only | plugin | yes/reload | high | none for MVP | MVP | Trust should not be changed from browser initially. |
| Plugin install/update/remove | Plugins | service/CLI | no frontend API | dangerous_requires_confirmation | project | no after implemented | high | explicit management API and provenance UX | future | Defer. |
| Plugin git timeout | Plugins | `PLUGIN_GIT_TIMEOUT_SECONDS` | AppConfig/PluginService | read_only | project | yes | low | future typed patch | P2 | Low-risk but not MVP. |
| Plugin policies enabled | Plugins | contribution `enabled` | policy runtime | future | plugin | yes/reload | medium | settings patch | P2 | Affects automatic skill activation. |
| Skill enabled | Skills | skill frontmatter `enabled` | loader respects enabled | future | project/plugin | yes/reload | medium | project override patch | P1 | Avoid editing SKILL.md directly from browser. |
| Skill allowed tools | Skills | skill frontmatter | registry metadata | read_only | project/plugin | yes/reload | high | future skill config schema | MVP | Affects permissions/tool scope. |
| Skill aliases | Skills | registry/plugin loader | implicit | read_only | project/plugin | yes/reload | low | future registry DTO extension | P2 | Display if API exposes aliases. |
| Hook enabled | Hooks | hook contribution `enabled` | HookService registry | future | project/plugin | yes/reload | medium | settings patch | P1 | Hooks affect prompt/control flow. |
| Hook priority | Hooks | hook contribution | registry metadata | read_only | project/plugin | yes/reload | medium | future patch | P2 | Editing can change behavior order. |
| Hook trusted flag | Hooks | hook contribution | registry metadata | read_only | project/plugin | yes/reload | high | none | MVP | Do not make browser editable. |
| MCP server enabled | MCP | MCP server config | `MCPServerConfig.enabled` | future | mcp_server | yes/reload | high | `PATCH /mcp/servers/{name}/enabled` via config patch | P1 | Needs no-start snapshot status endpoint first. |
| MCP transport | MCP | MCP config | stdio supported, HTTP false | read_only | mcp_server | yes | high | none | MVP | Show support status. |
| MCP command/args/cwd | MCP | MCP config | parsed/validated | config_file_only | mcp_server | yes | high | future guarded editor | not_recommended | Editing from browser can execute arbitrary local commands. |
| MCP env/headers | MCP | MCP config | redacted | env_only/config_file_only | mcp_server | yes | high | none | not_recommended | Secrets and auth headers. |
| MCP discovery | MCP | `/mcp` | explicit discover today | dangerous_requires_confirmation | run/global | no | medium | `GET /mcp/snapshot`, `POST /mcp/discover` | P1 | Avoid background discovery on panel refresh. |
| Langfuse enabled | Observability | `LANGFUSE_ENABLED` | AppConfig/status | read_only | project | yes | medium | future typed patch | MVP | Show enabled/disabled. |
| Langfuse keys | Observability | env, `.env` | presence only | env_only | project | yes | high | none | not_recommended | Never edit/show in browser. |
| Langfuse base URL | Observability | env/config | status has configured boolean | read_only | project | yes | medium | future typed patch | MVP | Keep value redacted or host-only if exposed. |
| Capture inputs/outputs | Observability | LangfuseConfig | status exposes bools | dangerous_requires_confirmation | project | yes | high | typed patch with warning | P2 | Privacy-sensitive. |
| Include project paths | Observability | LangfuseConfig | status/config | dangerous_requires_confirmation | project | yes | high | typed patch with warning | P2 | Can leak local paths. |
| Runtime events mode | Observability | LangfuseConfig | status/config | future | project | yes | medium | typed patch | P1 | Reasonable future setting with validation. |
| Storage dir | Sessions | `CC_LANGGRAPH_STORAGE_DIR` | AppConfig/session storage | read_only | project | yes | high | none | MVP | Local path; avoid raw absolute path in UI. |
| Current session/thread | Sessions | runtime state | DTOs/events | read_only | session | no | low | existing session endpoints | MVP | Display for support/debug. |
| Export directory/path | Sessions | storage service | export endpoint | read_only | project/session | no | medium | future export listing | P2 | Use storage-relative paths. |
| Eval scenario list | Eval | files under `evals/` | CLI only | future | project | no | low | future eval API | future | Keep out of settings MVP. |
| UI theme | UI | none/local state | frontend-only | yes | ui_only | no | low | none | MVP | Store in local storage. |
| UI density | UI | none/local state | frontend-only | yes | ui_only | no | low | none | MVP | Store in local storage. |
| Event verbosity | UI | frontend reducer | frontend-only | yes | ui_only | no | low | none | MVP | Collapse debug/low-signal events. |
| Auto-scroll | UI | frontend state | frontend-only | yes | ui_only | no | low | none | MVP | Browser preference only. |
| Sidebar visibility/layout | UI | frontend state | frontend-only | yes | ui_only | no | low | none | MVP | Browser preference only. |

