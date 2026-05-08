# Config

Phase 8 makes configuration layering explicit and explainable.

## Precedence

Effective runtime config is loaded in this order, with later layers winning:

```text
CLI explicit args / programmatic overrides
> process environment variables
> project config
> user config
> project-root .env
> defaults
```

Project config is read from:

```text
.lg-agent/config.toml
```

If that file does not exist, `langgraph-agent.toml` in the project root is accepted for compatibility. User config is read from `%APPDATA%/langgraph-agent-blueprint/config.toml` on Windows or `~/.config/langgraph-agent-blueprint/config.toml` elsewhere.

Secrets should normally come from process env or `.env`, not committed project config.

## TOML Examples

```toml
model_name = "fake-model"
permission_mode = "strict"
network_enabled = false

[web_fetch]
allow_private_hosts = false
max_bytes = 1000000

[context]
max_tokens = 8000
max_file_bytes = 200000

[plugins]
paths = ["examples/plugins/example-plugin"]
git_timeout_seconds = 60

[observability.langfuse]
enabled = false
environment = "dev"
```

The loader also accepts `[langfuse]` for direct `LangfuseConfig` fields and `[mcp]` for MCP config payloads.

## Diagnostics

Slash commands:

```text
/config show
/config explain
/config validate
```

CLI commands:

```powershell
lg-agent config show
lg-agent config explain
lg-agent config validate
```

`show` prints the redacted effective config. `explain` lists sources and value origins. `validate` prints structured diagnostics for invalid values and config source failures.

All secret-like values are redacted in reports and command output.

