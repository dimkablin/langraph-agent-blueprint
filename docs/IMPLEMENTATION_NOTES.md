# Implementation Notes

## Audit Verification Pass

Date: 2026-05-05

The implementation is based on the existing audit documents:

- `docs/SOURCE_AUDIT.md`
- `docs/SKILLS_AUDIT.md`
- `docs/FEATURE_TRACEABILITY_MATRIX.md`
- `docs/MIGRATION_SPEC.md`

Verification performed before implementation:

- Confirmed source path exists: `C:\Users\dimka\Documents\PROJECTS\llm-data-analyst\claude-code-like-project`.
- Confirmed target path exists: `C:\Users\dimka\Documents\PROJECTS\claude-code-langraph`.
- Confirmed `package.json` is still absent in the audited source tree.
- Confirmed the target project initially contained only `docs/` audit files.
- Confirmed the audit conclusion still holds: the source is a Claude Code-like terminal assistant, not a browser React data analyst app.

No contradictions were found that require rewriting the audit documents.

## Implementation Assumptions

- The Python package name is `claude_code_langgraph`; the repository folder keeps the existing `langraph` typo.
- LangGraph is the only workflow/orchestration runtime for assistant turns, tool routing, permission gates, skill invocation, session lifecycle, compaction, memory, and subagent execution.
- Services and tools are intentionally thin execution layers. They do not own assistant workflow.
- Tests use the fake provider. No test requires Anthropic, OpenAI, Ollama, network access, MCP servers, or cloud credentials.
- Cloud and local model providers are supported through configuration, but optional provider packages may be absent at runtime. Provider errors should be explicit and non-secret.
- Data analyst behavior remains an optional extension and is not claimed as a direct port.

## Implementation Scope

The implementation creates a complete, testable Python/LangGraph runtime with:

- interactive and headless CLI adapters
- LangGraph state, nodes, routes, interrupts, subgraphs, and streaming events
- model provider abstraction with fake, OpenAI, OpenAI-compatible, Ollama, and optional Anthropic providers
- tool registry and core tools for files, search, shell, web, todos, skills, MCP, diagnostics, and agents
- permission service with LangGraph interrupt/resume support
- skill registry, file-based loader, bundled skills, and SkillTool
- command registry and required slash commands
- session storage, resume, export, memory, compaction, hooks, plugin and MCP abstractions

Unsupported or intentionally minimal areas are documented in the dedicated docs files.
