# Tools

Tools implement `BaseTool` with:

- name
- description
- Pydantic input/output schemas
- safety classification
- read-only flag
- permission requirement
- sync/async run methods
- timeout/output limit metadata

Core tools:

- `read_file`
- `write_file`
- `edit_file`
- `notebook_read`
- `notebook_edit`
- `glob`
- `grep`
- `bash`
- `powershell`
- `web_fetch`
- `web_search`
- `todo_write`
- `agent`
- `skill`
- `diagnostics`
- `mcp.*` adapters

Tool workflow is graph-owned: UI/API call the graph, the graph routes to permission and execution nodes, and services perform low-level operations.

Runtime status after fixes:

- Provider tool schemas are bound to supported models with registry names preserved.
- Tool results are returned as `ToolMessage` and then routed back to `model_call`.
- File/search/shell/notebook/todo tools have end-to-end fake-provider tests.
- Ollama `qwen3:14b` was manually verified for native `read_file` tool calling.
- `web_fetch` is disabled unless network is enabled and approved; when enabled it returns untrusted-content warning metadata.
- `web_search` reports unavailable when no provider is configured.
