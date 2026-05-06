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

## Security

Plugin install and discovery never execute plugin scripts. Skills are prompt content only. Plugin skill tool calls still go through the normal tool registry, permission service, LangGraph interrupt/resume flow, and skill `allowed_tools` scope.

Git install/update is a network operation and fails with a structured error unless `NETWORK_ENABLED=true`. Path traversal in manifest-declared skill paths is rejected.

## Commands

Slash command:

```text
/plugins
```

CLI commands:

```powershell
lg-agent plugins list
lg-agent plugins install <source>
lg-agent plugins update <name>
lg-agent plugins remove <name>
```
