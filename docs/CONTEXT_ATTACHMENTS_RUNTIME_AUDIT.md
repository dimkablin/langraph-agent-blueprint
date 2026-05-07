# Context Attachments Runtime Audit

Current audit date: 2026-05-07

This is the short pre-implementation audit for Phase 6 context providers and attachments.

## Current Context Builder

`src/langgraph_agent_blueprint/graph/nodes/context_builder.py` builds model-facing system context from:

- project root
- durable memory
- tool registry summary
- skill registry summary
- todos
- plugin bootstrap fragments
- hook-provided context fragments

There is no first-class context-provider layer yet. `context_builder` does not resolve file references, directories, globs, notebooks, MCP resources, URLs, pasted text, images, or PDFs.

## Current Input Normalization

`normalize_input_node` creates one `HumanMessage` from `input_text`, marks `metadata.input_normalized`, preserves the existing `attachments` list, and runs `user_prompt` hooks.

It does not parse `@README.md`, `@glob:...`, `@mcp:...`, `@url:...`, or quoted path mentions.

## Existing State Fields

`AssistantState` already has:

- `attachments: list[dict[str, Any]]`
- `context_status: dict[str, Any]`
- `metadata: dict[str, Any]`

There are no typed fields for:

- context references
- resolved context items
- context fragments
- context budget report

## Existing Provider Building Blocks

Useful existing services:

- `FileService`: safe project-root-confined text/notebook operations.
- `SearchService`: glob/grep helpers.
- `NotebookService`: notebook cell extraction without execution.
- `WebService`: guarded `http`/`https` fetch with network enablement, private-host guardrails, redirects, timeout, and byte cap.
- `MCPService`: stdio client discovery plus `resources/read`.

These should be reused from context providers rather than duplicated in graph nodes.

## Source Capabilities To Close

Source re-sync identified context providers and attachments as Phase 6:

- at-mentions and file refs
- directory refs
- glob refs
- notebooks as context
- MCP resources as external context
- URL context through existing web guardrails
- pasted text/text attachments
- image/PDF attachment records with safe placeholder summaries
- context budget accounting
- context-window and source/trust metadata for future UI

## Risks

- Path traversal or absolute-path reads outside project root.
- Full local path leaks in events, sessions, or observability.
- Huge file/resource/URL payloads entering graph state or trace metadata.
- Binary/image/PDF content being decoded as text.
- External content prompt injection being treated as instructions.
- MCP/URL context bypassing existing network/MCP safety boundaries.
- Child subagents sharing mutable parent attachment/context structures.

## Phase 6 Needed Components

- Pydantic boundary models in `models/context.py`.
- Context reference parser for conservative `@...` syntax.
- Context provider service/registry with file, directory, glob, notebook, MCP resource, URL, text, image, and PDF providers.
- Context budget service using cheap token estimates and truncation/drop reporting.
- Graph-owned resolution node or isolated resolver call before `context_builder`.
- Context fragments injected into system context with trust and prompt-injection markers.
- Session persistence of refs, attachment metadata, and budget report.
- Runtime events for resolution start, fragment add, errors, and budget application.
- Subagent context inheritance by copied selected metadata, not shared mutable objects.
