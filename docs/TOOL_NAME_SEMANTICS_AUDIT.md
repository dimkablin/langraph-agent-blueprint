# Tool Name Semantics Audit

Audit date: 2026-05-06.

Scope: `src/langgraph_agent_blueprint`, `tests`, and current `docs`. This is an audit-only pass. No production runtime code or tests were changed.

## Post-Implementation Status

Implementation date: 2026-05-06.

The P0/P1 production findings from this audit have been fixed:

- `PermissionService` now reads `tool.permission.action`, `tool.permission.risk`, `requires_permission`, `is_read_only`, and `allowed_in_plan_mode` from `ToolPermissionMetadata`.
- Permission confirmation payloads are built from the resolved `ToolCall` plus resolved tool metadata; secret-like args are recursively redacted and summaries are stable JSON.
- `tool_router` now resolves the registry tool and routes by `tool.runtime.route` (`execute`, `skill_graph`, `agent_graph`, `mcp_graph`) instead of hardcoded names or `mcp.` prefixes.
- `ToolExecutionService` now applies typed `ToolStateEffect` records from tool runtime metadata/hook output. Todo replacement, child-run merge, and file-read history are no longer selected by `tool.name`.
- `_permission_action` and `_permission_risk` were removed from the production path.

Verification:

```bash
python -m pytest tests\test_tool_permission_metadata.py tests\test_permission_service_metadata_driven.py tests\test_tool_router_metadata_routes.py tests\test_tool_state_effects_metadata.py -q
python -m pytest tests\test_file_tools.py tests\test_permission_interrupts.py tests\test_shell_permissions.py tests\runtime_audit\test_skills_e2e_runtime.py tests\runtime_audit\test_commands_e2e.py -q
rg -n "_permission_action|_permission_risk" src\langgraph_agent_blueprint
rg -n "tool\.name ==" src\langgraph_agent_blueprint
rg -n "tool_name in" src\langgraph_agent_blueprint
rg -n "mcp\." src\langgraph_agent_blueprint
```

The remaining `mcp.` production reference is the MCP adapter display/registry identity (`self.name = f"mcp.{definition.name}"`), not route classification. The fake provider still supports test-only shorthand aliases such as `tool:bash echo hi` and `tool:write_file path content`; these produce deterministic provider tool-call fixtures and do not define permission, risk, route, or state-effect semantics.

The original audit findings below are retained as historical evidence.

## Summary

- Total semantic tool-name references checked: 42
- OK references: 30
- Anti-pattern references: 12
- P0: 2 grouped findings
- P1: 6 grouped findings
- P2: 4 grouped findings

The largest runtime issues are in:

- `src/langgraph_agent_blueprint/services/permission_service.py`
- `src/langgraph_agent_blueprint/graph/nodes/tool_router.py`
- `src/langgraph_agent_blueprint/services/tool_execution_service.py`
- `src/langgraph_agent_blueprint/services/model_provider.py` fake-provider contract

## Searches Performed

Required searches were run with `rg`. One combined PowerShell pattern containing `== "` was split into smaller equivalent `rg` commands because PowerShell quote parsing treated part of the pattern as a pipeline. The split searches covered `tool_name`, `tool.name`, `call.name`, `name in`, `startswith`, `endswith`, and `==`.

Commands/searches included:

```bash
rg -n "read_file|write_file|edit_file|notebook_read|notebook_edit|glob|grep|bash|powershell|web_fetch|web_search|todo_write|skill|agent|diagnostics|mcp" src tests docs
rg -n "tool_name" src/langgraph_agent_blueprint tests
rg -n "tool\.name" src/langgraph_agent_blueprint tests
rg -n "call\.name" src/langgraph_agent_blueprint tests
rg -n "name in" src/langgraph_agent_blueprint tests
rg -n "startswith" src/langgraph_agent_blueprint tests
rg -n "endswith" src/langgraph_agent_blueprint tests
rg -n "_permission_action|_permission_risk|requires_permission|is_read_only|safety|risk|action|allowed_in_plan_mode|requires_network" src/langgraph_agent_blueprint tests
rg -n "if .*tool|elif .*tool|match .*tool|case .*tool|in \{.*read_file|in \{.*bash|in \{.*web" src/langgraph_agent_blueprint
rg -n "mcp\.|plugin|external|network|shell|write|edit|read_only|read-only" src/langgraph_agent_blueprint
rg -n "bind_tools|tool schema|tools=.*|available_tools|ToolCall|tool_calls|function" src/langgraph_agent_blueprint
rg -n "fake|tool:|deterministic|parse.*tool|ToolCall" src/langgraph_agent_blueprint tests
```

## What Counts As OK

Tool names are acceptable when used as:

- registry keys: `tool_registry.get(call.name)`
- provider schema names: function schema name must match the registry tool name
- display/logging/persistence identity: events, `ToolResult.name`, `ToolMessage` payloads
- allowed-tools matching: skill metadata intentionally names allowed tools
- concrete test fixture identity
- documentation examples
- concrete tool class declarations such as `name = "read_file"`

## What Counts As Anti-Pattern

Tool names are not acceptable as the source of:

- permission action
- permission risk
- side-effect type
- state merge behavior
- tool route kind such as skill, agent, MCP, plugin, shell, network, file, or todo
- MCP/plugin/external detection through name prefixes
- fake-provider behavior that only works for specific hardcoded tool names

## Findings

| File | Line | Snippet | Classification | Severity | Why | Proposed replacement | Test needed |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `src/langgraph_agent_blueprint/services/permission_service.py` | 38-40 | `action=_permission_action(str(tool_call["name"]))`, `risk=_permission_risk(...)` | `anti_pattern_permission_policy` / `anti_pattern_risk_classification` | P0 | Permission request semantics are derived from registry key, so custom/MCP/plugin tools default to wrong `unknown`/`low` classifications. | Add `tool.permission` metadata and build confirmation payload from the resolved tool, not just `ToolCall.name`. | Permission tests with custom tool metadata and MCP/plugin conservative defaults. |
| `src/langgraph_agent_blueprint/services/permission_service.py` | 47-58 | `if tool_name in {"write_file"}` / `{"bash", "powershell"}` / `{"web_fetch", "web_search"}` | `anti_pattern_side_effect_classification` | P0 | Action is guessed from built-in names. New write/shell/network tools are misclassified. | `ToolPermissionMetadata.action`. | Assert action comes from metadata for built-in and custom tools. |
| `src/langgraph_agent_blueprint/services/permission_service.py` | 61-66 | `if tool_name in {"bash", "powershell"}` | `anti_pattern_risk_classification` | P0 | Risk is guessed from built-in names. External shell-like tools can be marked `low`. | `ToolPermissionMetadata.risk`. | Assert shell/network/write/MCP risks are metadata-driven. |
| `src/langgraph_agent_blueprint/services/tool_execution_service.py` | 48-49 | `if tool.name in {"read_file", "edit_file", "write_file"}` | `anti_pattern_side_effect_classification` | P0 | Prior-read/read-files metadata is updated only for hardcoded file tools. A custom file reader/editor cannot participate in edit-safety state. | Tool output or runtime metadata should declare state update effects, e.g. `state_effects=["read_history"]`. | Custom file-like tool updates read history through metadata/effect hook. |
| `src/langgraph_agent_blueprint/graph/nodes/tool_router.py` | 43 | `if name in {"skill", "SkillTool"}` | `anti_pattern_routing_semantics` | P1 | Tool route to skill graph is inferred from names instead of tool kind/runtime behavior. | `ToolRuntimeMetadata.kind == "skill"` or `route="skill_graph"`. | Register a custom skill-tool alias and verify routing uses metadata. |
| `src/langgraph_agent_blueprint/graph/nodes/tool_router.py` | 53 | `if name in {"agent", "task"}` | `anti_pattern_routing_semantics` | P1 | Agent/task route is hardcoded. Plugin subagent tools cannot route correctly. | `ToolRuntimeMetadata.kind == "agent"` or `route="agent_graph"`. | Custom agent-like tool routes by metadata. |
| `src/langgraph_agent_blueprint/graph/nodes/tool_router.py` | 56 | `if name.startswith("mcp.")` | `anti_pattern_mcp_plugin_detection` | P1 | MCP behavior is inferred from prefix. This couples identity formatting to runtime behavior and misses non-prefixed MCP adapters. | MCP adapter should expose `runtime.kind="mcp"` and conservative permission metadata. | MCP mock tool without `mcp.` prefix still routes through MCP metadata, or prefix becomes display-only. |
| `src/langgraph_agent_blueprint/services/tool_execution_service.py` | 46-47 | `if tool.name == "todo_write"` | `anti_pattern_side_effect_classification` | P1 | State update for todos is tied to one name instead of declared output/state effect. | Tool result/state-effect metadata, e.g. `state_update_keys=["todos"]` or output protocol. | Custom task/todo tool updates todos through metadata. |
| `src/langgraph_agent_blueprint/services/tool_execution_service.py` | 50-51 | `if tool.name == "agent"` | `anti_pattern_routing_semantics` | P1 | Child-run state merge depends on one hardcoded name. | Tool runtime metadata or output protocol declares `child_runs` state effect. | Agent-like tool result merges child runs without name special-case. |
| `src/langgraph_agent_blueprint/graph/nodes/skill_router.py` | 47 | `if active["name"] == "remember"` | `needs_review` | P1 | This is skill-name semantics, not tool-name semantics, but it is the same extensibility problem for skill runtime. | Skill metadata/runtime behavior should declare direct memory write behavior. | A memory-like custom skill uses metadata behavior, not name. |
| `src/langgraph_agent_blueprint/services/model_provider.py` | 74-82 | `if command.startswith("bash ")` -> emits `name="bash"` | `anti_pattern_fake_provider_contract` | P2 | Fake-provider shorthand special-cases one shell tool. This is test ergonomics, but production fake provider is a runtime provider. | Generic `tool:<name> <json>` should be the only semantic path; optional aliases should be documented test-only fixtures. | Fake provider tests use generic JSON syntax for shell. |
| `src/langgraph_agent_blueprint/services/model_provider.py` | 83-86 | `if command.startswith("write_file ")` -> emits `name="write_file"` | `anti_pattern_fake_provider_contract` | P2 | Fake-provider shorthand knows write_file args and behavior. | Move shorthand into tests/helpers or keep only generic JSON parser. | Write-file fake tests use `tool:write_file {"path":...}` only. |
| `src/langgraph_agent_blueprint/services/model_provider.py` | 87-88 | `if command.startswith("agent ")` -> emits `name="agent"` | `anti_pattern_fake_provider_contract` | P2 | Fake-provider shorthand encodes agent tool shape by name. | Generic tool JSON or fixture helper. | Agent fake tests construct generic tool call. |
| `tests/test_command_permission_models.py` | 38-39 | `assert request.action == "write"` / `risk == "medium"` from `write_file` | `anti_pattern_risk_classification` | P2 | Test locks current name-derived permission behavior. | Rewrite after refactor to assert metadata drives action/risk. | New test should register metadata-bearing fake tool. |

## P0 Findings

1. `PermissionService` derives permission action and risk from tool names.
2. `ToolExecutionService` updates prior-read/read-files safety metadata only for hardcoded file tool names.

These affect security/runtime correctness for custom, MCP, and plugin tools.

## P1 Findings

1. `tool_router` routes skill tools by names `skill`/`SkillTool`.
2. `tool_router` routes agent tools by names `agent`/`task`.
3. `tool_router` routes MCP tools by `mcp.` prefix.
4. `tool_execution_service` merges todo state only for `todo_write`.
5. `tool_execution_service` merges child runs only for `agent`.
6. `skill_router` has analogous skill-name behavior for `remember` and should be reviewed separately.

## P2 Findings

1. Fake provider has hardcoded shorthand contracts for `bash`, `write_file`, and `agent`.
2. One permission model test asserts action/risk produced from `write_file` name.

## OK References

| File | Line | Snippet | Classification | Why |
| --- | ---: | --- | --- | --- |
| `src/langgraph_agent_blueprint/tools/registry.py` | 34-46 | `self._tools[tool.name]`, `get(name)`, `snapshot()` | `ok_registry_lookup` | Tool names are registry keys and metadata identity. |
| `src/langgraph_agent_blueprint/services/model_provider.py` | 130-140 | provider function schema `"name": name` | `ok_provider_schema_name` | Provider schema name must preserve registry identity. |
| `src/langgraph_agent_blueprint/services/tool_execution_service.py` | 27-28 | `self.registry.get(call.name)` | `ok_registry_lookup` | `call.name` is used as lookup key only. |
| `src/langgraph_agent_blueprint/services/tool_execution_service.py` | 38-44 | record `"name": tool.name` | `ok_display_or_logging` | Tool result identity/persistence. |
| `src/langgraph_agent_blueprint/services/tool_execution_service.py` | 66-74 | tool event id/name/status | `ok_display_or_logging` | Event identity only. |
| `src/langgraph_agent_blueprint/graph/nodes/model_call.py` | 25-26 | filter `available_tools` by `allowed_tools` | `ok_allowed_tools_matching` | Skill metadata intentionally names allowed tools. |
| `src/langgraph_agent_blueprint/graph/nodes/model_call.py` | 41-43 | `AIMessage.tool_calls` name | `ok_provider_schema_name` | LangChain message contract requires tool call names. |
| `src/langgraph_agent_blueprint/graph/nodes/tool_router.py` | 26 | disallowed check against skill allowed tools | `ok_allowed_tools_matching` | This is policy matching against explicit skill metadata. |
| `src/langgraph_agent_blueprint/cli.py` | 49, 74 | display `payload.get("tool_name")` | `ok_display_or_logging` | UI text only. |
| `src/langgraph_agent_blueprint/ui/event_renderer.py` | 14 | display permission tool name | `ok_display_or_logging` | UI text only. |
| `src/langgraph_agent_blueprint/tools/*.py` | class `name = "..."` | concrete tool names | `ok_registry_lookup` | Tool identity declarations are expected. |
| `src/langgraph_agent_blueprint/skills/definitions/*/SKILL.md` | `allowed_tools` lists | tool names in skill metadata | `ok_allowed_tools_matching` | This is explicit user/skill configuration. |
| `tests/*` and `tests/runtime_audit/*` | most concrete tool names | fixture identity | `ok_test_fixture` | Tests verify known built-ins unless they assert name-derived policy. |
| `docs/*` | tool examples/status | documentation examples | `ok_docs_example` | Not production behavior. |

## Open Questions

- Should every tool expose a single `permission` metadata object, or should current `safety/is_read_only/requires_permission` be wrapped for compatibility?
- Should state effects be declared on tools (`state_effects`) or returned by tool outputs (`state_update`) without executor special-cases?
- Should skill runtime receive analogous `SkillRuntimeMetadata` for special behaviors like `remember`?
- Should MCP adapter continue using `mcp.` as display/registry prefix while routing by metadata?
- Should fake-provider shorthand aliases be removed, moved to test helpers, or retained as documented compatibility aliases?
