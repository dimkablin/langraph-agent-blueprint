# Commands

Commands are registered in `CommandRegistry` and parsed by `parse_slash_command`.

Eval/replay commands are Typer CLI subcommands, not slash commands inside chat:

```bash
lg-agent eval list
lg-agent eval run basic-chat
lg-agent eval run --all
```

Implemented commands:

| Command | Type | Behavior |
| --- | --- | --- |
| `/help` | local | Lists commands. |
| `/clear` | local | Clears current conversation state. |
| `/compact` | session | Runs manual context compaction and emits compact events. |
| `/resume` | session | Loads latest or named session state. |
| `/export` | local | Writes a transcript export file. |
| `/skills` | local | Lists available skills. |
| `/status` | local | Shows provider/model/session/project root/cwd/storage/tool/skill/command counts. |
| `/cost` | local | Shows usage telemetry and honest unavailable cost when pricing is absent. |
| `/config` | local | Shows redacted runtime config and path separation. |
| `/doctor` | diagnostic | Calls diagnostics service. |
| `/observability` | diagnostic | Shows redacted Langfuse observability status. |
| `/memory` | local | Shows durable memory. |
| `/todo` | local | Shows persisted todos. |
| `/plugins` | local | Lists installed/enabled plugins, skill counts, bootstrap status, and discovery errors. |
| `/hooks` | local | Lists registered hooks, hook points, plugin names, priority, and enabled status. |
| `/mcp` | local | Lists configured MCP servers, discovered tools, resources, prompts, and status. |
| `/context` | local | Lists resolved context references, fragments, budget usage, and context errors. |
| `/prompt` | prompt | Expands command args into a model prompt. |
| `/skill` | skill | Routes to `skill_graph`. |

Recognized but minimal commands: `/rewind`, `/branch`, `/rename`, `/tag`.

Runtime status after fixes:

- `/compact` routes to compaction and emits compact events.
- `/resume` loads latest/specific session state.
- `/export` writes a transcript file.
- `/doctor` calls diagnostics.
- `/observability` reports Langfuse enabled mode, SDK availability, configured URL/key presence, capture flags, and last error.
- `/memory` and `/todo` read durable restored state.
- `/plugins` reports discovered external plugin contributions.
- `/hooks` reports hook registry state exposed by `load_registries`.
- `/mcp`, `/mcp tools`, `/mcp resources`, and `/mcp prompts` report MCP discovery state exposed by `load_registries`.
- `/context` reports graph-resolved context references/fragments and the active context budget report.
- `/help` separates enabled commands from unsupported optional commands.
