# Settings Frontend Plan

Audit date: 2026-05-09

This plan describes the Settings Center direction. The initial MVP is now implemented as a read-only backend/runtime settings center plus local-only UI preferences.

## Implemented MVP Update

Implemented in the frontend:

- `SettingsCenter` in the existing right-side settings drawer.
- Read-only Model, Runtime, Plugins, Skills, Hooks, MCP, Context, and Observability sections.
- Local-only UI preferences for theme, density, event verbosity, debug-event visibility, and auto-scroll.
- Preferences persist to browser `localStorage`.
- Settings data comes from existing graph-facing APIs and does not mutate backend config.
- MCP status uses passive `GET /mcp/snapshot`, not discovery-starting `GET /mcp`.

Still deferred:

- backend config mutation
- API key editing
- plugin install/update/remove
- MCP command/args/cwd editing
- dangerous runtime toggles
- generic `GET /settings` / `PATCH /settings`

## Recommendation

Start with a read-only Settings Center plus UI-only preferences. This is the implemented MVP.

Reasoning:

- Existing backend endpoints are strong for diagnostics and status.
- Existing mutation contract is not yet designed.
- Settings changes can alter runtime safety, prompt behavior, MCP process startup, observability privacy, and plugin trust.
- A thin frontend should not invent stateful enable/disable behavior outside backend config.

## Minimum MVP

### 1. Model

Display:

- provider
- effective model
- provider-specific configured model
- API key presence, redacted
- current per-run `model_intelligence`

Editable in MVP:

- `model_intelligence` in composer/run scope

Read-only in MVP:

- provider
- model
- base URL
- API keys

Deferred:

- temperature
- max output tokens
- top_p
- provider model picker
- provider capability discovery

### 2. Runtime

Display:

- permission mode
- network enabled
- streaming available
- shell timeout
- tool output limit
- compaction thresholds

Editable in MVP:

- UI event verbosity
- auto-scroll
- compact/dense display

Read-only in MVP:

- permission mode
- network mode
- shell/tool limits

### 3. Plugins

Display:

- plugin name/version/description
- enabled/disabled from manifest/config
- trust level
- contribution counts
- warnings/errors
- source/lock metadata if available and redacted

Editable in MVP:

- none

Deferred:

- enable/disable plugin through typed config patch
- install/update/remove plugin
- trust override

### 4. Skills

Display:

- skill name
- source type: built-in, file, plugin
- description
- allowed tools
- model/effort metadata if present
- enabled/disabled status if backend exposes it

Editable in MVP:

- none

Deferred:

- enable/disable skill through project config overrides

### 5. Hooks

Display:

- hook id
- hook point
- plugin/source
- enabled flag
- priority
- trusted flag
- allowed actions/policy summary

Editable in MVP:

- none

Deferred:

- enable/disable hook with warning
- priority editing

### 6. MCP

Display:

- server list
- enabled flag
- transport
- trust level
- status
- discovered tool/resource/prompt counts
- invalid config diagnostics

Editable in MVP:

- none

Implemented passive panel dependency:

- `GET /mcp/snapshot` returns current configured/snapshot state without starting MCP processes.

Deferred:

- explicit discover/reconnect action
- enable/disable server
- command/args/cwd editing

### 7. Context

Display:

- max context tokens
- max file bytes
- max directory files
- max glob files
- current session budget
- trust marker explanation

Editable in MVP:

- none, except UI display preferences

Deferred:

- project-level budget changes through typed config patch
- per-session budget override

### 8. Observability

Display:

- Langfuse enabled/disabled
- SDK installed
- base URL configured
- key presence, redacted
- environment/release
- capture inputs/outputs
- runtime events mode
- last error, redacted

Editable in MVP:

- none

Deferred:

- runtime events mode
- capture inputs/outputs
- include project paths

### 9. UI Preferences

Editable in MVP:

- theme
- density
- event verbosity
- show/hide debug events
- auto-scroll
- sidebar layout preference

Storage:

- local storage or frontend app state

These should not be written to backend config.

## Frontend Structure

Suggested files:

```text
frontend/src/components/settings/
  SettingsCenter.tsx
  SettingsSection.tsx
  ModelSettingsSection.tsx
  RuntimeSettingsSection.tsx
  PluginSettingsSection.tsx
  SkillSettingsSection.tsx
  HookSettingsSection.tsx
  MCPSettingsSection.tsx
  ContextSettingsSection.tsx
  ObservabilitySettingsSection.tsx
  UIPreferencesSection.tsx

frontend/src/api/settings.ts
frontend/src/api/config.ts
frontend/src/runtime/settings.ts
frontend/src/runtime/uiPreferences.ts
```

## State Model

Frontend state should separate:

- backend settings snapshot
- backend diagnostics
- UI-only preferences
- future pending config patch
- future validation result

Do not merge UI preferences into backend config DTOs.

## Visual Integration

Current frontend already has:

- right-side runtime drawer
- sidebar settings action
- status panel
- registry/context/session panels

Settings Center can replace `RuntimeStatusPanel` inside the existing settings drawer. The current `RuntimeStatusPanel` can become a small overview section inside the new center.

From the external widget audit, `WidgetAccountSettings.tsx` is visual reference only. Do not copy its old auth, data analyst settings, local mock tools, or backend assumptions.

## Tests To Add Later

Frontend tests:

- settings center renders redacted config
- model settings display provider/model/key presence
- plugin/skill/hook sections render backend data
- MCP section does not auto-trigger discovery if snapshot endpoint exists
- dangerous settings are read-only or disabled
- UI-only preferences update local state
- no secret-like values appear in DOM
- unknown setting descriptor renders safely

Backend contract tests:

- settings snapshot redacts secrets
- settings schema classifies editability correctly
- validation rejects secret edits
- validation rejects dangerous edits without confirmation
- MCP snapshot endpoint does not start processes
- config patch writes only allowed project config keys

## Deferred UX

Do not include in the first Settings Center:

- API key editor
- plugin marketplace/install/update/remove
- MCP command editor
- trusted executable plugin settings
- eval dashboard
- full provider model browser
- arbitrary config file editor

## Implementation Order

1. Completed: Build read-only Settings Center using existing endpoints.
2. Completed: Add frontend UI preferences with local persistence.
3. Completed: Add passive MCP snapshot endpoint for settings.
4. Add backend `GET /settings` and `GET /settings/schema` if the read-only frontend starts duplicating too much mapping.
5. Add validation-only settings patch endpoint.
6. Add safe project config patch endpoint.
7. Add extension enable/disable through the generic settings patch.
