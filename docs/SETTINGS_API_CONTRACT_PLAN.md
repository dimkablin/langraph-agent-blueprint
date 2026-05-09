# Settings API Contract Plan

Audit date: 2026-05-09

This document tracks the backend/frontend contract for Settings Center. The first Settings MVP is implemented with existing read-only endpoints plus passive `GET /mcp/snapshot`; mutation endpoints remain future work.

## Existing Read-only Endpoints

| Endpoint | Current behavior | Settings Center use | Caveat |
| --- | --- | --- | --- |
| `GET /config` | returns redacted effective config | show current values | not a settings schema; values are generic dict |
| `GET /config/explain` | returns config sources, origins, diagnostics | show source precedence and overridden values | read-only |
| `GET /config/validate` | returns diagnostics and ok flag | settings health panel | read-only |
| `GET /plugins` | discovers plugins and returns status/contributions/warnings | plugin status panel | discovery may inspect filesystem/cache |
| `GET /hooks` | returns registered hooks | hooks panel | read-only |
| `GET /mcp/snapshot` | returns current configured/snapshot MCP state without discovery | passive MCP settings panel | implemented for Settings MVP |
| `GET /mcp` | discovers MCP servers/tools/resources/prompts | explicit discovery/status | can start stdio MCP processes |
| `GET /observability` | returns redacted Langfuse status | observability panel | read-only |
| `GET /skills` | returns enabled skill registry | skills panel | disabled skills are not a first-class DTO |
| `GET /tools` | returns tool registry | tools/debug panel | read-only |
| `GET /commands` | returns slash commands | commands/debug panel | read-only |

## Main Contract Gap

The backend has diagnostics but not a typed Settings Center contract.

Missing concepts:

- settings snapshot DTO grouped by category
- settings schema with editability, scope, restart requirement, security classification, bounds, and enum choices
- typed settings patch DTO
- validate-before-save endpoint
- project config write policy
- extension enable/disable overrides
- audit event for settings changes
- snapshot-only MCP status endpoint

## Recommended API Strategy

Use a two-step strategy.

### Step 1: Read-only Settings MVP

Implement frontend Settings Center using existing endpoints plus UI-only preferences.

No backend mutations. No new security surface.

Frontend can display:

- model/provider/API key presence
- config sources and validation
- plugins with contribution counts, trust, warnings
- skills and allowed tools
- hooks and hook points
- MCP configured/discovered status, with a warning that discovery is explicit
- observability status
- context budgets
- UI-only preferences

Implemented backend improvement:

```text
GET /mcp/snapshot
```

This returns current MCP state without starting new server processes. Current `/mcp` remains the explicit discovery/status path.

### Step 2: Safe Config Patch

Add typed mutation only after config write policy is designed.

Recommended endpoints:

```text
GET /settings
GET /settings/schema
POST /settings/validate
PATCH /settings
```

Semantics:

- `GET /settings` returns redacted grouped current settings.
- `GET /settings/schema` returns metadata for UI rendering and editability.
- `POST /settings/validate` validates a patch without saving.
- `PATCH /settings` writes allowed project-level values to `.lg-agent/config.toml` only after validation.

Do not mutate runtime services directly from the frontend. All backend changes should flow through typed config and runtime reload/rebuild policy.

## Proposed DTOs

### Setting Descriptor

```python
class SettingDescriptor(FrozenRuntimeModel):
    key: str
    label: str
    category: Literal["model", "runtime", "plugins", "skills", "hooks", "mcp", "context", "observability", "ui"]
    value: Any
    value_repr: str
    source: str | None = None
    editable: Literal["yes", "read_only", "dangerous_requires_confirmation", "config_file_only", "env_only", "future", "not_recommended"]
    scope: Literal["global", "project", "session", "run", "ui_only", "plugin", "mcp_server"]
    requires_restart: bool
    secret: bool = False
    security_risk: Literal["low", "medium", "high"]
    choices: list[str] = Field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    diagnostics: list[ConfigDiagnostic] = Field(default_factory=list)
```

### Settings Snapshot

```python
class SettingsSnapshotDTO(FrozenRuntimeModel):
    categories: dict[str, list[SettingDescriptor]]
    config: EffectiveConfigReport
    plugins: PluginStatusDTO
    skills: SkillRegistryDTO
    hooks: HookStatusDTO
    mcp: MCPStatusDTO
    observability: ObservabilityStatusDTO
```

### Settings Patch

```python
class SettingPatchValue(FrozenRuntimeModel):
    key: str
    value: Any
    scope: Literal["project", "session", "run", "ui_only", "plugin", "mcp_server"]
    confirmation: str | None = None

class SettingsPatchRequest(FrozenRuntimeModel):
    values: list[SettingPatchValue]
    dry_run: bool = False

class SettingsPatchResult(FrozenRuntimeModel):
    applied: bool
    diagnostics: list[ConfigDiagnostic]
    requires_runtime_restart: bool = False
    changed_keys: list[str] = Field(default_factory=list)
```

## Extension Enable/Disable API

Do not add ad hoc in-memory toggles. Prefer project config overrides.

Future endpoint shape:

```text
PATCH /settings
```

Patch examples:

```json
{
  "values": [
    {"key": "plugins.example.enabled", "scope": "plugin", "value": false},
    {"key": "skills.verify.enabled", "scope": "project", "value": true},
    {"key": "hooks.example.pre_tool.enabled", "scope": "plugin", "value": false},
    {"key": "mcp.servers.example.enabled", "scope": "mcp_server", "value": false}
  ]
}
```

The backend should compile these into project config overrides and then require runtime reload or rebuild, depending on implementation.

## Endpoint Recommendations

| Endpoint | Method | Purpose | Priority | Notes |
| --- | --- | --- | --- | --- |
| `/settings` | GET | grouped settings snapshot | P1 | Can wrap existing endpoints server-side. |
| `/settings/schema` | GET | editability/schema metadata | P1 | Lets frontend render without hardcoding policy. |
| `/settings/validate` | POST | validate patch without saving | P1 | Required before mutation. |
| `/settings` | PATCH | apply safe config patch | P2 | Defer until write policy is ready. |
| `/mcp/snapshot` | GET | read MCP state without discovery/startup | implemented | Used by Settings Center. |
| `/mcp/discover` | POST | explicit MCP discovery | P1 | Optional future route; current `/mcp` remains explicit discovery. |
| `/plugins/{name}/enabled` | PATCH | plugin enable/disable | P2 | Prefer generic settings patch instead. |
| `/skills/{name}/enabled` | PATCH | skill enable/disable | P2 | Prefer generic settings patch instead. |
| `/hooks/{id}/enabled` | PATCH | hook enable/disable | P2 | Prefer generic settings patch instead. |
| `/observability` | PATCH | observability flags | P2 | Prefer generic settings patch with warnings. |
| `/context/settings` | PATCH | context budgets | P2 | Prefer generic settings patch. |

## Validation Rules

Settings mutation must validate:

- key exists in schema
- value type is correct
- value is within bounds
- source is mutable by frontend
- secret values are rejected unless a dedicated secure mechanism exists
- dangerous setting has required confirmation
- project config write target is inside project root
- resulting config passes `AppConfig` validation
- redaction works in response diagnostics

## Security Rules

The API should reject browser edits for:

- API keys
- MCP env/headers with secrets
- MCP command/args/cwd in MVP
- plugin install/update/remove
- trusted executable plugin flags
- storage dir/project root/cwd
- full local path exposure

Dangerous but possible later with confirmation:

- network enabled
- private host web fetch
- observability capture inputs/outputs
- include project paths in observability
- extension enable/disable that changes prompt/tool behavior

## Events

Future settings mutations should emit high-signal runtime events:

- `settings_validation_failed`
- `settings_changed`
- `settings_change_requires_restart`
- `extension_enabled`
- `extension_disabled`

Events must include only redacted metadata.
