# Pydantic Boundary Contracts

This project uses Pydantic at runtime boundaries, not as a blanket replacement for ordinary Python objects.

Boundary contracts are used where raw or cross-layer data enters the agent runtime:

- provider output -> `ToolCall`
- tool execution -> `ToolResult`
- tool result -> `ToolMessage`
- graph events -> `RuntimeEvent`
- user slash input -> `ParsedCommand`
- command handler output -> `CommandResult`
- permission interrupt/resume -> `PermissionRequest` / `PermissionDecision`
- session storage records -> `SessionMetadata`, `RuntimeEvent`, and `ToolResult`
- skill tool or `/skill` args -> built-in skill-specific Pydantic args schemas
- tool classification -> `ToolPermissionMetadata`, `ToolRuntimeMetadata`, and `ToolStateEffect`
- plugin config/manifests/discovery -> `PluginSource`, `PluginManifest`, `PluginContribution`, and `PluginInstallResult`
- hook discovery/invocation/results -> `HookContribution`, `HookContext`, `HookInvocation`, `HookResult`, and `HookRunSummary`

The LangGraph state remains checkpointer-safe: nodes store dictionaries and lists in state, and validate them at node/service boundaries with `model_validate(...)`. Outgoing DTOs are serialized with `model_dump(mode="json")`.

## Base Models

`langgraph_agent_blueprint.models.base` defines:

- `RuntimeModel`: mutable boundary DTO for snapshots/config-like payloads.
- `FrozenRuntimeModel`: immutable DTO for requests, results, and events.
- `dump_model(...)`: JSON-safe serialization helper.
- `validate_list(...)`: validates state lists before node logic uses them.

## Tool Calls And Results

Provider-specific tool calls are normalized with `normalize_provider_tool_call(...)` into:

- `id`
- `name`
- `args`
- `provider`
- `raw`
- `status`

The graph stores `ToolCall.model_dump(mode="json")` in `pending_tool_calls`. `tool_router`, `permission_gate`, and `tool_executor` validate those records before reading fields.

Tool execution returns `ToolResult` with explicit statuses: `ok`, `error`, `rejected`, `disabled`, or `unavailable`. `tool_result_to_tool_message(...)` is the single conversion point from `ToolResult` to LangChain `ToolMessage`.

## Tool Metadata

Tool behavior at runtime boundaries is metadata-driven:

- `ToolPermissionMetadata` declares action, risk, read-only status, permission requirement, plan-mode allowance, network requirement, external-tool status, and sensitive arg keys.
- `ToolRuntimeMetadata` declares tool kind, LangGraph route, and post-execution state effects.
- `ToolStateEffect` is the typed envelope for graph state deltas produced by tool behavior.

`BaseTool` keeps legacy `safety`, `is_read_only`, and `requires_permission` properties as compatibility wrappers, but production permission, routing, and state-effect consumers read `tool.permission` and `tool.runtime`.

## Events

All graph-visible events are `RuntimeEvent` records. The legacy `event(...)` helper now builds and validates a `RuntimeEvent` before returning a state-safe dict. Session storage validates event JSONL records on write and read; corrupt rows are skipped during load so resume is not blocked by one bad log line.

## Commands

`parse_slash_command(...)` returns `ParsedCommand | None`. Command handlers return `CommandResult`, which keeps the old ergonomic constructor but derives an explicit route such as `finalize`, `model`, `skill`, `compact`, `resume`, `export`, or `diagnostics`.

## Permissions

Permission checks return typed policy payloads. Interrupt state uses `PermissionRequest`, and resume payloads are normalized into `PermissionDecision`. Existing `{ "approved": true }` resume payloads remain supported, but the runtime stores the resolved decision explicitly.

## Skills

Built-in skills use explicit schemas:

- `RememberSkillArgs`
- `VerifySkillArgs`
- `DebugSkillArgs`
- `SimplifySkillArgs`
- `SkillifySkillArgs`
- `StuckSkillArgs`
- `BatchSkillArgs`
- `UpdateConfigSkillArgs`

String arguments are mapped by skill name, not by generic key guessing. Unknown file-based skills use `GenericSkillArgs`. Prompt interpolation is separate and handled by `format_skill_args_for_prompt(...)`; it is formatting, not security sanitization.

Invalid skill arguments return structured errors through the skill graph/tool loop instead of crashing the runtime.

## Plugins

External plugin source strings normalize into `PluginSource`. Harness manifests such as `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, and `package.json` are parsed into `PluginManifest`. Discovered plugin roots become `PluginContribution` records before they enter graph state or `SkillRegistry`. Explicit install/update/remove operations return `PluginInstallResult`.

Plugin records stored in LangGraph state are JSON-safe dictionaries produced from those models. Plugin skill content remains prompt data; tool execution and permissions continue to use the normal tool and permission boundary models.

Plugin hook entries from manifests are validated into `HookContribution` records before registration. Malformed hook entries remain structured warnings, not raw unvalidated runtime data.

## Hooks

Hook runtime boundaries live in `langgraph_agent_blueprint.models.hooks`:

- `HookContribution` describes a registered core/plugin hook.
- `HookContext` is the read-only context graph nodes pass to hooks.
- `HookInvocation` pairs one contribution with one context.
- `HookResult` is the controlled output envelope.
- `HookPolicy` and `HookRuntimeMetadata` describe trust/action metadata.
- `HookRunSummary` carries typed results plus validated runtime events.

Graph state stores hook records as JSON-safe dictionaries. Nodes apply `HookResult` through the controlled applier; hooks cannot replace arbitrary graph state fields.

## Sessions

`SessionMetadata` validates known metadata fields and preserves historical flat extra fields in `extra`. `SessionStorage` validates events as `RuntimeEvent` and tool execution records as `ToolResult` at JSONL boundaries.

## Adding New Boundaries

Add a Pydantic DTO when a value crosses a runtime boundary or enters durable storage. Keep ordinary internal helper logic as Python functions/classes when a schema would only add noise.
