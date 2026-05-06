# Commands Runtime Audit

Current acceptance status as of 2026-05-06. Pre-fix audit findings are historical; the current table below is based on live graph runs and regression tests.

## Current Command Matrix

| Command | Expected behavior | Current graph route | State update | Events | Persistence | Test / smoke evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/help` | List enabled commands and unsupported optional commands without LLM. | `command_router -> persist_session -> finalize_response` | `final_response` | `command_started`, `command_finished`, `final_response` | session event | CLI stream-json emitted multiple JSONL events; smoke listed active and unsupported commands. | `working` |
| `/clear` | Clear conversation without losing session/project. | local command route | `messages=[]` via clear command update | command + final events | session event | Smoke returned `Conversation cleared.` and messages were empty. | `working` |
| `/compact` | Manual compaction, no fake/model response. | command route to `compact_decision -> compact_context` | `context_status.compacted=True` | `compact_finished` | compact/session state | Smoke returned `Context compacted.` | `working` |
| `/resume` | Load latest or named session and continue. | command route with session hydration | session id/messages/todos/memory/usage/metadata | command + final events | restored state | Smoke resumed `resume-accept2` and restored todo `resume todo`. | `working` |
| `/export` | Write transcript file safely. | local command uses `ExportService` | `exported_outputs` | command + final events | markdown export file | Smoke wrote `.storage_acceptance2\exports\session_...md`. | `working` |
| `/skills` | List enabled and disabled skills. | local command route | `final_response` | command + final events | session event | Smoke showed eight enabled and seven disabled optional skills. | `working` |
| `/status` | Show provider/model/session/project_root/cwd/storage/tool/skill/command counts. | local command route | `final_response` | command + final events | session event | Smoke showed acceptance workspace as `project_root` and storage separately. | `working` |
| `/cost` | Show usage and honest unknown cost. | local command route | `final_response` | command + final events | usage/session | Smoke returned `Usage: {}` and `Cost: unavailable`. | `working` |
| `/config` | Show redacted effective config with clear paths. | local command route | `final_response` | command + final events | session event | Smoke showed acceptance project root and `.storage_acceptance2`. | `working` |
| `/doctor` | Run diagnostics service. | local command uses `DiagnosticsService` | `metadata.diagnostics` | command + final events | diagnostics metadata | Smoke had `metadata.diagnostics`. | `working` |
| `/memory` | Show durable memory. | local command reads `MemoryService` | `final_response` | command + final events | durable memory file | After typed `remember`, smoke showed stored memory text. | `working` |
| `/todo` | Show durable todos. | local command reads restored todos | `final_response` | command + final events | `todos.json` | After `todo_write`, later `/todo` showed `final acceptance todo`. | `working` |
| `/prompt` | Expand args into model prompt. | prompt command route to model | adds prompt message | model/final events | session messages | Regression `test_prompt_command_continues_to_model`. | `working` |
| `/skill` | Invoke skill graph. | command route to `skill_graph` | `active_skill`, scoped metadata | `skill_started`, `skill_finished` | skill/session events | Runtime skill tests cover all built-ins. | `working` |

## Unsupported Optional Commands

`/rewind`, `/branch`, `/rename`, `/tag`, `/context`, `/plugins`, and `/mcp` are recognized as optional/unsupported in help output. They are not counted as required working commands.

## Historical Audit Result

Before the runtime fixes, `/compact`, `/resume`, `/export`, `/doctor`, `/memory`, and `/todo` were partially implemented or unreachable. That is historical context only; current acceptance evidence is above.
