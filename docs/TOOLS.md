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

