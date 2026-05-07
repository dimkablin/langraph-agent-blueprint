# Code Quality Audit

Date: 2026-05-07

## Summary

The codebase has good naming and small node modules in many places, but the recent runtime phases left several long services, broad `Any` surfaces, shallow state merges, and some behavior/documentation mismatches.

## Findings

### P1: File Edit Does Not Enforce Unique Match

- File: `src/langgraph_agent_blueprint/services/file_service.py:52`
- Problem: `edit_text` checks only `old_text not in content`, then calls `content.replace(old_text, new_text, 1)`.
- Why it matters: The tool description promises exact text replacement after prior read. If `old_text` appears multiple times, the first occurrence is edited silently, which can alter the wrong code block.
- Suggested fix: Count occurrences and reject `count != 1`, unless the input schema adds an explicit occurrence/index mode.

### P1: MCP Config Validation Errors Are Silently Dropped

- File: `src/langgraph_agent_blueprint/services/mcp_service.py:357`
- Problem: `_parse_server_configs` catches `ValidationError` and continues without preserving a diagnostic.
- Why it matters: A typo in config can look like "no MCP servers configured", slowing diagnosis and weakening `/doctor`.
- Suggested fix: Preserve invalid-server warnings in MCP snapshot/diagnostics and tests.

### P1: Git Plugin Commands Have No Timeout

- File: `src/langgraph_agent_blueprint/services/plugin_service.py:388`
- Problem: `_run_git` uses `subprocess.run(..., capture_output=True)` without timeout.
- Why it matters: A hung network or credential prompt can block plugin install/update indefinitely.
- Suggested fix: Add a configurable timeout and include command phase in structured `PluginInstallResult` errors.

### P1: Hook Applier Can Mutate Nested State Lists Through Shallow Copies

- File: `src/langgraph_agent_blueprint/hooks/applier.py:15`
- File: `src/langgraph_agent_blueprint/hooks/applier.py:42`
- Problem: `metadata = dict(state.get("metadata", {}))` is shallow, then `metadata.setdefault("hook_system_context_fragments", []).append(...)` can append to a list object shared with the input state.
- Why it matters: LangGraph nodes should return state deltas, not mutate incoming state, especially for reducers/checkpointing/debugging.
- Suggested fix: Deep-copy nested metadata values touched by appliers or rebuild lists immutably.

### P2: Observability Service Is Too Broad

- File: `src/langgraph_agent_blueprint/services/observability_service.py`
- Problem: One module owns Langfuse imports, client creation, callback creation, RuntimeEvent mapping, redaction, trace context management, child observation emission, status, and a placeholder hook.
- Why it matters: The trace-scoping fix is now correct, but future Langfuse changes will touch a large surface.
- Suggested fix: Split mapper/redactor, Langfuse factory/status, and scoped turn into separate modules.

### P2: MCPService Is Too Broad

- File: `src/langgraph_agent_blueprint/services/mcp_service.py`
- Problem: One class parses config, manages connection states, discovers tools/resources/prompts, invokes tools, formats resources/prompts, stores events, and keeps legacy mock tools.
- Why it matters: Protocol growth, HTTP transport, and prompt-to-skill registration will make this hard to reason about.
- Suggested fix: Split into `MCPConfigLoader`, `MCPClientManager`, `MCPDiscoveryService`, `MCPInvocationService`, and diagnostics snapshot.

### P2: PluginService Is Too Broad

- File: `src/langgraph_agent_blueprint/services/plugin_service.py`
- Problem: One class parses source strings, installs local/git plugins, manages cache paths, reads manifests, applies Superpowers adapter behavior, parses hooks, writes lock metadata, and removes plugins.
- Why it matters: Installation trust policy and contribution discovery evolve at different speeds.
- Suggested fix: Split source install/cache management from manifest/contribution adapters.

### P2: Broad Dict/Any State Remains Common At Graph Boundaries

- Files: `src/langgraph_agent_blueprint/graph/*.py`, `models/llm.py`, `models/plugins.py`, `models/mcp.py`
- Problem: Pydantic boundaries exist, but graph nodes still accept and return `dict[str, Any]`, and some DTOs keep raw dicts for plugin/MCP/provider data.
- Why it matters: This is normal for LangGraph state, but it makes unchecked metadata flags easy to introduce.
- Suggested fix: Add small typed state-slice helpers for high-risk areas: metadata routes, active_skill, mcp_state, plugin_state, observability_state.

### P2: ToolExecutionService Catches All Exceptions As Tool Errors

- File: `src/langgraph_agent_blueprint/services/tool_execution_service.py:54`
- Problem: `except (ValidationError, Exception)` converts any exception into a `ToolResult`.
- Why it matters: This protects the graph from tool failures but can hide programming errors during development.
- Suggested fix: Keep broad isolation for production, but add optional debug/crash mode or narrow exceptions around tool boundaries.

### P2: SearchService Returns Empty Results On Ripgrep Failure

- File: `src/langgraph_agent_blueprint/services/search_service.py:54`
- Problem: `_grep_rg` ignores non-zero return codes and stderr.
- Why it matters: Invalid regex or ripgrep failure looks like no matches.
- Suggested fix: Treat regex/rg errors as structured tool errors, while preserving "no match" as empty results.

### P2: Model Token Events Are Synthetic And Potentially Noisy

- File: `src/langgraph_agent_blueprint/graph/nodes/model_call.py:44`
- Problem: `model_token` events are generated by splitting final response text after the model call.
- Why it matters: This is not true streaming and can inflate event volume.
- Suggested fix: Either mark as synthetic, disable by default, or only emit token events from real streaming providers.

### P2: Session Event Dedup Is O(n) Per Append

- File: `src/langgraph_agent_blueprint/storage/session_storage.py:67`
- Problem: `append_event` scans all existing events for every event id.
- Why it matters: Long sessions will become slower as event logs grow.
- Suggested fix: Deduplicate per turn before storage, maintain an index, or accept duplicate append and dedupe on read.

### P2: Session Listing Skips Metadata Validation

- File: `src/langgraph_agent_blueprint/storage/session_storage.py:123`
- Problem: `list_sessions` reads metadata JSON directly without `SessionMetadata.from_record`.
- Why it matters: Invalid stored metadata can leak inconsistent shapes to API/CLI list output.
- Suggested fix: Validate each metadata record and skip/report invalid rows.

### P3: CLI Module Has A UTF-8 BOM

- File: `src/langgraph_agent_blueprint/cli.py:1`
- Problem: Tooling that reads files as plain UTF-8 can fail.
- Suggested fix: Remove the BOM in a formatting cleanup.

### P3: Test File Contains Mojibake For Cyrillic Chat Inputs

- File: `tests/test_observability_cli.py:36`
- Problem: The intended Russian strings are mojibake.
- Why it matters: Test behavior still checks session grouping, but readability suffers.
- Suggested fix: Replace with ASCII or correct UTF-8 in a test-only cleanup.

