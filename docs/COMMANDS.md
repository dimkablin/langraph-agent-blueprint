# Commands

Commands are registered in `CommandRegistry` and parsed by `parse_slash_command`.

Implemented commands:

| Command | Type | Behavior |
| --- | --- | --- |
| `/help` | local | Lists commands. |
| `/clear` | local | Clears current conversation state. |
| `/compact` | session | Requests compaction in graph metadata. |
| `/resume` | session | Records resume intent. |
| `/export` | local | Records export intent. |
| `/skills` | local | Lists available skills. |
| `/status` | local | Shows session/model status. |
| `/cost` | local | Shows usage telemetry. |
| `/config` | local | Shows redacted runtime config. |
| `/doctor` | diagnostic | Points to diagnostics tool/service. |
| `/memory` | local | Shows memory scopes. |
| `/todo` | local | Shows todos. |
| `/prompt` | prompt | Expands command args into a model prompt. |
| `/skill` | skill | Routes to `skill_graph`. |

Recognized but minimal commands: `/rewind`, `/branch`, `/rename`, `/tag`, `/context`, `/plugins`, `/mcp`.

