# Config And Plugin SDK Runtime Audit

Audit date: 2026-05-08

## Current Config Loading

`AppConfig.from_env()` currently reads defaults, project-root `.env`, process environment variables, and explicit programmatic overrides. It already preserves the important rule that process environment variables beat `.env`, including alias handling such as `LANGFUSE_ENVIRONMENT` over `LANGFUSE_TRACING_ENVIRONMENT` within one source layer.

Current gaps:

- no typed source report for where effective values came from
- no user config file
- no project config file beyond `.env`
- invalid values are often silently defaulted
- `/config` only prints a redacted snapshot, not explain/validate output
- no `lg-agent config ...` CLI group

Phase 8 target precedence:

```text
explicit CLI/programmatic overrides
> process env
> project config
> user config
> project .env
> defaults
```

## Current Plugin SDK

`PluginService` discovers local/cache plugin roots, reads `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, and `package.json`, validates skill path confinement, and exposes typed `PluginContribution` records. Current contribution types:

- skills
- hooks
- policies
- bootstrap/system context, including Superpowers bootstrap

Current gaps:

- plugin manifests do not have a documented typed SDK schema for commands/tools/MCP/context providers/trust
- plugin commands are not registered
- plugin tools cannot be declaratively registered
- plugin MCP server configs cannot be contributed
- plugin context providers cannot be resolved through `@plugin:...`
- plugin diagnostics are split across hook/policy warnings only
- no example plugin demonstrates the full SDK contract

## Existing Coverage

Existing tests cover:

- env precedence for Langfuse aliases
- plugin skill loading
- Superpowers bootstrap/policy behavior
- generic plugin policies
- declarative plugin hooks
- plugin git timeout
- MCP config/diagnostics
- context providers and eval/replay harness

Missing Phase 8 tests:

- full config layering across `.env`, user config, project config, env, and overrides
- config explain/validate commands
- plugin command/tool/MCP/context provider models and registry wiring
- plugin SDK security diagnostics for malformed/path-traversal contributions
- eval scenarios proving plugin SDK additions without graph edits

## Phase 8 Implementation Status

Implemented in this phase:

- `AppConfig.load_with_report()` with explicit defaults -> `.env` -> user config -> project config -> process env -> override layering.
- Redacted `ConfigSource`, `ConfigValueOrigin`, `ConfigDiagnostic`, and `EffectiveConfigReport` output.
- `/config show|explain|validate` and `lg-agent config show|explain|validate`.
- Typed plugin SDK contribution models for commands, tools, MCP servers, context providers, trust policy, and SDK diagnostics.
- Declarative plugin commands (`static_response`, `prompt`, `skill`).
- Declarative plugin tools (`static_text`, `context_lookup`, `disabled_placeholder`).
- Plugin MCP config merge with plugin-root `cwd` confinement.
- Plugin context providers resolved with `@plugin:<plugin>:<provider>`.
- `examples/plugins/example-plugin` and plugin SDK eval scenarios.
