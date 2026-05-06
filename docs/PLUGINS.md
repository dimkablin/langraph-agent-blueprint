# Plugins

Plugins are external, data-only contributions discovered by `PluginService` and wired into the LangGraph runtime through registries and graph state. They are not vendored into `src/langgraph_agent_blueprint/skills/definitions`.

## Install And List

Local plugin directory:

```powershell
lg-agent plugins install C:\path\to\plugin
lg-agent plugins list
```

Git plugin source:

```powershell
$env:NETWORK_ENABLED = "true"
lg-agent plugins install superpowers@git+https://github.com/obra/superpowers.git#v5.1.0
lg-agent plugins list
```

The runtime also loads configured plugin roots from `PLUGIN_PATHS` / `LG_AGENT_PLUGIN_PATHS`.

Installed plugins are cached under:

```text
.storage/
  plugins/
    <plugin-name>/
      repo/
      manifest.json
      lock.json
```

`lock.json` records source, ref, resolved git commit when available, install time, validated manifest metadata, and license text when a license file exists.

## Discovery

The service accepts:

- `superpowers@git+https://github.com/obra/superpowers.git#v5.1.0`
- `git+https://github.com/obra/superpowers.git#main`
- `https://github.com/obra/superpowers`
- local plugin directories

Discovery reads harness manifests such as `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json`, falls back to `package.json`, validates paths, and exposes `PluginContribution` records in graph state.

## Hook Contributions

Plugin manifests can declare data-only hooks:

```json
{
  "name": "example-plugin",
  "hooks": [
    {
      "id": "example.add_context",
      "point": "pre_model",
      "action": "add_system_context",
      "content": "Remember to be concise.",
      "priority": 100
    }
  ]
}
```

`PluginService` validates hook entries into `HookContribution` records. Valid hooks are registered in `HookRegistry`; malformed hooks are reported as `hook_warnings` in plugin state and `/plugins` output instead of crashing discovery.

External plugin hooks are untrusted by default. Phase 1 supports only safe declarative actions: `continue`, `add_event`, `add_system_context`, `modify_metadata`, and `block`. Script fields, install hooks, package scripts, and arbitrary plugin code are ignored and never executed.

## Security

Plugin install and discovery never execute plugin scripts. Skills and hook-added context are prompt content only. Plugin skill tool calls still go through the normal tool registry, permission service, LangGraph interrupt/resume flow, and skill `allowed_tools` scope.

Git install/update is a network operation and fails with a structured error unless `NETWORK_ENABLED=true`. Path traversal in manifest-declared skill paths is rejected.

## Commands

Slash command:

```text
/plugins
/hooks
```

CLI commands:

```powershell
lg-agent plugins list
lg-agent plugins install <source>
lg-agent plugins update <name>
lg-agent plugins remove <name>
```
