# Plugin SDK

Phase 8 defines the current data-only plugin SDK contract. Plugins contribute runtime capabilities through manifest data; discovery never executes plugin Python, JavaScript, package scripts, or install hooks.

## Manifest

```json
{
  "name": "example_plugin",
  "version": "0.1.0",
  "skills": "./skills",
  "hooks": [],
  "policies": [],
  "commands": [],
  "tools": [],
  "mcp_servers": {},
  "context_providers": [],
  "bootstrap": {
    "context": "Optional prompt context"
  },
  "trust": {
    "level": "untrusted"
  },
  "enabled": true
}
```

Supported contribution types:

- `skills`: directory of `SKILL.md` definitions, registered as `<plugin_name>/<skill_name>`.
- `hooks`: declarative graph-owned hook contributions.
- `policies`: declarative policy entries evaluated by `plugin_policy_node`.
- `commands`: static, prompt, or skill slash commands.
- `tools`: declarative static/context lookup/disabled plugin tools.
- `mcp_servers`: plugin-relative MCP server config contributions.
- `context_providers`: static or plugin-file context providers.
- `bootstrap.context`: optional plugin-provided system context.

Malformed non-critical contributions become warnings in `/plugins`; a malformed plugin should not crash graph execution.

## Commands

Command types:

- `static_response`: returns manifest text.
- `prompt`: expands `{args}` into a prompt and continues through the model path.
- `skill`: routes to a plugin or built-in skill.

Command conflicts are deterministic: built-ins keep their names, and conflicting plugin commands are registered under `<plugin_name>.<command>`.

## Tools

Plugin tools are declarative only:

- `static_text`: returns a static manifest response.
- `context_lookup`: returns a manifest-declared text file under the plugin root.
- `disabled_placeholder`: registers an unavailable tool with a clear error.

Tools are registered as:

```text
plugin.<plugin_name>.<tool_name>
```

They declare normal `ToolPermissionMetadata` and `ToolRuntimeMetadata`; routing and permissions remain metadata-driven.

## MCP

Plugins may contribute MCP server configs under `mcp_servers`. Config is merged into runtime MCP config but discovery remains explicit through graph registry loading and `/mcp` diagnostics. Plugin-relative `cwd` is confined to the plugin root. Plugin MCP servers are external and untrusted by default.

## Context Providers

Plugin context can be attached with:

```text
@plugin:<plugin_name>:<provider_name>
```

`plugin_file` providers are confined to the plugin root, marked `plugin_provided`, budgeted, and rendered as data with prompt-injection warnings.

## Example Plugin

See:

```text
examples/plugins/example-plugin/
```

It demonstrates a skill, hook, policy, static command, prompt command, skill command, static tool, context provider, and local fake MCP server config.

## Security Model

- No arbitrary plugin code execution during discovery.
- No install/update scripts.
- Plugin paths are confined to plugin root.
- Disabled plugins contribute nothing.
- Secrets are redacted from diagnostics.
- Plugin content is prompt data, not instruction.
- MCP and side-effecting tools still go through normal permissions.

