# Fix Implementation Log

Current as of 2026-05-06.

## P0 Fixed

- State reducers and event lifecycle preserve graph/runtime events through final state and streaming.
- Provider layer passes `SystemMessage`, binds LangChain-compatible tool schemas, parses provider tool calls, and supports fake/Ollama/openai/openai-compatible/anthropic adapters.
- Tool execution appends provider-compatible `ToolMessage` records before returning to `model_call`.
- Default `project_root` resolves from explicit config or `Path.cwd()`, never from `storage_dir`.
- Permission flow uses LangGraph interrupt/resume, emits `permission_required` and `permission_resolved`, and persists decisions.
- Skill runtime routes explicit `/skill` and model `skill` tool calls through graph state, emits skill events, enforces `allowed_tools`, and persists session state.

## P1 Fixed

- Required slash commands now execute real runtime behavior:
  `/help`, `/clear`, `/compact`, `/resume`, `/export`, `/skills`, `/status`, `/cost`, `/config`, `/doctor`, `/memory`, `/todo`.
- File/search/shell/notebook/todo tools work through full graph/model/tool loop with events and persistence.
- Session persistence restores messages, todos, memory references, usage, and metadata enough to continue.
- Memory service integrates with `remember` and `/memory`.
- Export creates transcript markdown files.
- Stream-json emits runtime events as JSONL.

## Final Acceptance Fixes Added

- `src/claude_code_langgraph/skills/args.py`: added typed Pydantic skill argument schemas, explicit string-to-schema mappings, size limits, validation errors, and prompt formatting.
- `src/claude_code_langgraph/skills/invocation.py`: validates skill args against each skill's schema before rendering `SKILL.md`.
- `src/claude_code_langgraph/graph/nodes/skill_router.py`: returns structured ToolMessage validation errors and uses typed `remember` args for durable memory.
- `src/claude_code_langgraph/services/model_provider.py`: fake provider now treats `tool:bash {"command":"..."}` as JSON args, matching real provider contracts.
- `src/claude_code_langgraph/tools/search_tools.py`: relative `path` values for `glob`/`grep` resolve under `project_root`, preserving confinement and making `path="src"` work from any process cwd.
- `src/claude_code_langgraph/tools/web_tools.py`: `web_fetch` propagates untrusted-content warning metadata from `WebService`.

## Tests Added or Extended

- `tests/runtime_audit/test_skills_e2e_runtime.py`
  - `test_skill_tool_accepts_structured_args_from_model`
- `tests/runtime_audit/test_tools_e2e.py`
  - `test_grep_relative_path_is_resolved_under_project_root`
  - `test_bash_accepts_json_fake_tool_arguments_after_approval`
  - `test_web_fetch_enabled_marks_content_untrusted_after_approval`

## Verification

- `python -m pytest -q -rA`: passed, 73 collected tests.
- `npm.cmd --prefix frontend run test:static`: passed.
- `npm.cmd --prefix frontend run build`: passed when rerun outside sandbox after an initial sandbox `spawn EPERM`.
- Runtime smoke: 36/36 fake-provider scenarios passed.
- Ollama smoke: `qwen3:14b` emitted native `read_file` tool call, graph executed it, appended ToolMessage, and final response was `ACCEPTANCE_README_LINE`.

## Remaining Limitations

- `web_search` is disabled/unavailable without a configured provider.
- MCP is optional and disabled when no config exists.
- Plugin discovery is minimal.
- Subagent behavior remains limited/synthetic.
- Running from a source checkout requires editable install or `PYTHONPATH=src`; installed mode works with `python -m claude_code_langgraph`.
