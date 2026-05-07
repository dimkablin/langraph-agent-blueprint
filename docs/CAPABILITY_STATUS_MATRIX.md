# Capability Status Matrix

Current acceptance status as of 2026-05-06. Historical audit statuses such as `broken`, `partially_working`, and `registered_but_unreachable` described the pre-fix runtime and are no longer the current matrix.

Status vocabulary:

- `working`: verified end-to-end through CLI/API/runtime graph, execution, events, and persistence where applicable.
- `working_prompt_driven`: verified skill graph path with events, scoped tools, persistence, and prompt-driven model behavior.
- `working_with_provider_requirement`: works when the required provider/config exists.
- `disabled_by_config`: intentionally unavailable because config/provider is absent.
- `disabled_by_platform`: unavailable on the current platform only.
- `unsupported_optional`: recognized or documented, but not part of required acceptance.
- `broken`: required capability failed current acceptance.

## Slash Commands

| Capability | Type | Exists | Registered | Reachable from CLI/API | Executes | Events visible | Persisted where applicable | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/help` | command | yes | yes | yes | yes | yes | session event | `working` | Lists active commands and unsupported optional commands. |
| `/clear` | command | yes | yes | yes | yes | yes | clear/session event | `working` | Clears `messages` and returns `Conversation cleared.` |
| `/compact` | command | yes | yes | yes | yes | yes | compact summary/session | `working` | Routes to compaction path and emits `compact_finished`. |
| `/resume` | command | yes | yes | yes | yes | yes | restored state | `working` | Restores named session todos/messages/metadata enough to continue. |
| `/export` | command | yes | yes | yes | yes | yes | export file | `working` | Creates transcript markdown under storage exports. |
| `/skills` | command | yes | yes | yes | yes | yes | session event | `working` | Shows enabled and disabled skills. |
| `/status` | command | yes | yes | yes | yes | yes | session event | `working` | Shows provider/model/session/project_root/cwd/storage/tool/skill/command counts. |
| `/cost` | command | yes | yes | yes | yes | yes | session usage | `working` | Shows usage and `Cost: unavailable` when provider has no pricing. |
| `/config` | command | yes | yes | yes | yes | yes | session event | `working` | Shows redacted config with separate project root and storage. |
| `/doctor` | command | yes | yes | yes | yes | yes | diagnostics metadata | `working` | Calls `DiagnosticsService`. |
| `/memory` | command | yes | yes | yes | yes | yes | durable memory read | `working` | Shows memory written by `remember`. |
| `/todo` | command | yes | yes | yes | yes | yes | durable todos read | `working` | Shows todos persisted by `todo_write`. |
| `/prompt` | command | yes | yes | yes | yes | yes | session event | `working` | Expands prompt and continues to model path. |
| `/skill` | command | yes | yes | yes | yes | yes | skill invocation/session | `working` | Routes explicit skill invocation through skill graph. |
| `/plugins` | command | yes | yes | yes | yes | yes | plugin state | `working` | Lists installed/enabled plugin contributions. |
| `/hooks` | command | yes | yes | yes | yes | yes | hook state | `working` | Lists registered hook contributions. |
| `/mcp` | command | yes | yes | yes | yes | yes | MCP state | `working` | Lists MCP servers, tools, resources, and prompts. |
| `/rewind`, `/branch`, `/rename`, `/tag`, `/context` | optional commands | documented | unsupported list | yes | no side effect | command response | n/a | `unsupported_optional` | Listed separately by `/help`; not shown as active required commands. |

## Skills

| Capability | Type | Exists | Registered | Reachable from CLI/API | Reachable from model | Executes | Events visible | Persisted | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `batch` | skill | yes | yes | `/skill batch` | SkillTool | prompt-driven skill runtime | yes | yes | `working_prompt_driven` | Emits `skill_started`/`skill_finished`; scoped to `agent,todo_write`. |
| `debug` | skill | yes | yes | `/skill debug` | SkillTool | prompt-driven skill runtime | yes | yes | `working_prompt_driven` | Scoped to read/search/shell tools; side effects still require permission. |
| `remember` | skill | yes | yes | `/skill remember` | SkillTool | durable memory write | yes | yes | `working` | Typed args such as `{"text":"Dima 228","scope":"project"}` validate and persist; invalid scopes are rejected. |
| `simplify` | skill | yes | yes | `/skill simplify` | SkillTool | prompt-driven skill runtime | yes | yes | `working_prompt_driven` | Scoped to read/edit tools; edits require approval. |
| `skillify` | skill | yes | yes | `/skill skillify` | SkillTool | prompt-driven skill runtime | yes | yes | `working_prompt_driven` | Scoped to read/write/edit; writes require approval. |
| `stuck` | skill | yes | yes | `/skill stuck` | SkillTool | prompt-driven skill runtime | yes | yes | `working_prompt_driven` | Uses current context/todos/errors in skill prompt. |
| `update-config` | skill | yes | yes | `/skill update-config` | SkillTool | prompt-driven skill runtime | yes | yes | `working_prompt_driven` | Config writes must go through file tools and permission. |
| `verify` | skill | yes | yes | `/skill verify` | SkillTool | prompt-driven skill runtime | yes | yes | `working_prompt_driven` | Scoped to shell/search/read tools; shell requires approval. |

## Tools

| Capability | Type | Exists | Registered | Reachable from CLI/API | Reachable from model | Executes | Events visible | Persisted | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `read_file` | tool | yes | yes | yes | fake + Ollama | yes | yes | tool_calls/session | `working` | Fake and Ollama `qwen3:14b` read `README.md` and returned `ACCEPTANCE_README_LINE`. |
| `write_file` | tool | yes | yes | yes | fake/provider schema | approval + write/reject | yes | tool_calls/permissions | `working` | Approval writes file; rejection leaves no file and returns ToolMessage. |
| `edit_file` | tool | yes | yes | yes | fake/provider schema | prior read + approval | yes | tool_calls/metadata | `working` | Exact replacement works; missing text returns structured error recovery. |
| `notebook_read` | tool | yes | yes | yes | fake/provider schema | yes | yes | tool_calls/session | `working` | Reads valid `.ipynb` and returns notebook content metadata. |
| `notebook_edit` | tool | yes | yes | yes | fake/provider schema | approval + edit | yes | tool_calls/session | `working` | Edits cell and preserves notebook JSON. |
| `glob` | tool | yes | yes | yes | fake/provider schema | yes | yes | tool_calls/session | `working` | Finds `src/example.py` and `src/math_utils.py`. |
| `grep` | tool | yes | yes | yes | fake/provider schema | yes | yes | tool_calls/session | `working` | Relative `path=src` resolves under project root; Windows `rg --json` path parsing works. |
| `bash` | tool | yes | yes | yes | fake/provider schema | approval + execute | yes | tool_calls/permissions | `working` | JSON fake args execute `echo acceptance-shell` after approval. |
| `powershell` | tool | yes | yes | yes | fake/provider schema | approval + execute | yes | tool_calls/permissions | `working` | Windows PowerShell returns `acceptance-powershell`. |
| `web_fetch` | tool | yes | yes | yes | fake/provider schema | disabled by default; works when enabled | yes | tool_calls/permissions | `working_with_provider_requirement` | Disabled path reports config error; enabled local HTTP fetch returns untrusted warning metadata. |
| `web_search` | tool | yes | yes | yes | fake/provider schema | no provider configured | yes | tool_calls/permissions | `disabled_by_config` | Returns `Web search provider is not configured`, not empty success. |
| `todo_write` | tool | yes | yes | yes | fake/provider schema | yes | yes | todos/session | `working` | Later `/todo` shows persisted todo. |
| `skill` | tool | yes | yes | yes | fake + provider schema | routes to skill graph | yes | skill/session | `working` | Structured args route to skill graph; `remember` persists memory. |
| `agent` | tool | yes | yes | yes | fake/provider schema | real child graph run | yes | child_runs/session | `working_with_provider_requirement` | Child graph runs with isolated state, narrowed tool scope, parent ToolMessage merge, and child-run sidecar persistence. Nested approval resume remains future work. |
| `diagnostics` | tool | yes | yes | `/doctor` | provider schema | yes | yes | diagnostics metadata | `working` | `/doctor` calls diagnostics service. |
| `mcp.<server>.<tool>` | tool | discovered from config | yes when server configured | yes | provider schema | approval + MCP call | yes | tool_calls/permissions | `working_with_provider_requirement` | Fake stdio MCP server tests cover discovery, permission, approval, rejection, and result ToolMessage. |

## Final Counts

Slash commands:

- `working`: 12 required, 14 active including `/prompt` and `/skill`
- `unsupported_optional`: 7
- `broken`: 0

Tools:

- `working`: 11 required non-network/platform tools
- `working_with_provider_requirement`: 1 (`web_fetch`)
- `disabled_by_config`: 1 (`web_search` without provider)
- `disabled_by_platform`: 0 on Windows
- `broken`: 0

Skills:

- `working`: 1
- `working_prompt_driven`: 7
- `broken`: 0
