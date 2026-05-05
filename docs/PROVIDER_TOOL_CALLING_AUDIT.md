# Provider Tool Calling Audit

## Post-Fix Status (2026-05-06)

Provider tool binding is now implemented in `ModelProviderService`:

- `request.system_context` is prepended as a `SystemMessage` when no system message already exists.
- Registry tool metadata is converted to LangChain/OpenAI-style tool schemas while preserving model-callable registry names such as `read_file`, `write_file`, `grep`, `bash`, `skill`, and `todo_write`.
- Providers with `bind_tools` receive the converted tool list.
- LangChain `AIMessage.tool_calls` are normalized into graph `pending_tool_calls`.
- Tool execution appends a matching `ToolMessage`, then the graph routes back to `model_call`.
- The fake provider now emits AIMessage-compatible tool calls and supports JSON args for deterministic tests.

Updated provider matrix:

| Provider | System context passed | Tools bound | Tool calls parsed | Tool results returned | Streaming works | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fake` | yes for request contract | deterministic | yes | `ToolMessage` | graph event stream | `working` | Runtime blocker and tools E2E tests pass. |
| `ollama` | yes | yes via `ChatOllama.bind_tools` | yes | `ToolMessage` | graph event stream | `working` for tested `qwen3:14b` | Manual smoke read `README.md` with native tool call. |
| `openai_compatible` | yes | yes if LangChain model supports `bind_tools` | yes | `ToolMessage` | graph event stream | `implemented_not_live_tested` | Covered by mocked bind-tools provider test. |
| `openai` | yes | yes if package/key configured | yes | `ToolMessage` | graph event stream | `implemented_not_live_tested` | No cloud key required or used in tests. |
| `anthropic` | yes | yes if package/key configured | yes | `ToolMessage` | graph event stream | `implemented_not_live_tested` | No cloud key required or used in tests. |

Manual Ollama result:

```text
tool_results= [('read_file', 'ok', 'OLLAMA_TOOL_SMOKE_OK')]
messages= HumanMessage -> AIMessage(tool_calls=[read_file]) -> ToolMessage -> AIMessage(final)
```

## Provider Matrix

| Provider | System context passed | Tools bound | Tool calls parsed | Tool results returned | Streaming works | Status | Evidence | Root cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `fake` | no | synthetic parser only | yes for `tool:` syntax | via `request.metadata["tool_results"]`, not `ToolMessage` | no, final-state events only | `partially_working` | `tool:read_file {"path":"README.md"}` executes; `tool:write_file created.txt hello` interrupts. | Deterministic test parser bypasses real provider contracts. |
| `ollama` | no | no | only whatever unbound model returns; runtime saw none | no `ToolMessage` | no | `model_cannot_call` | Qwen answered normally to "read README.md"; `tool_results=[]`, `tool_route=no_tools`. | `ModelProviderService._langchain_generate` calls `model.invoke(messages)` only. |
| direct `ChatOllama` with manual `bind_tools` | yes if caller adds it | yes | yes | caller responsibility | n/a | model capability proven | Manual test returned `tool_calls=[{'name':'ReadFile','args':{'path':'README.md'}}]`. | Installed model/provider can tool-call; project runtime does not use it. |
| `openai_compatible` | no | no | maybe if model self-emits, not bound | no | no | `model_cannot_call` | Code path is same `_langchain_generate`. | No tool conversion/binding/system message. |
| `openai` | no | no | maybe if model self-emits, not bound | no | no | `model_cannot_call` | Code path is same `_langchain_generate`. | No `bind_tools`; no API-key runtime test performed. |
| `anthropic` | no | no | maybe if model self-emits, not bound | no | no | `model_cannot_call` | Code path is same `_langchain_generate`. | No Anthropic tool schema conversion. |

## Code Evidence

`src/claude_code_langgraph/graph/nodes/model_call.py` builds a provider-agnostic request:

```python
request = ModelRequest(
    messages=state.get("messages", []),
    system_context=state.get("context_status", {}).get("system_context", ""),
    tools=state.get("available_tools", {}),
    metadata={"tool_results": state.get("tool_results", [])},
)
```

`src/claude_code_langgraph/services/model_provider.py` ignores `system_context` and `tools` for every real provider:

```python
model = self._build_chat_model(provider)
messages = list(request.messages)
response = model.invoke(messages)
tool_calls = list(getattr(response, "tool_calls", []) or [])
```

There is no:

- `SystemMessage(content=request.system_context)`
- conversion from internal tool metadata to LangChain tools
- `model.bind_tools(...)`
- `ToolMessage` construction after tool execution
- structured-output fallback/parser for local models
- repair prompt/retry for malformed tool calls

## Ollama-Specific Findings

Installed `langchain_ollama.ChatOllama` supports `bind_tools`.

Manual direct-provider test:

```text
has_bind_tools= True
content= ''
tool_calls= [{'name': 'ReadFile', 'args': {'path': 'README.md'}, ...}]
```

Project runtime Ollama test:

```text
Prompt: "Прочитай README.md через доступный инструмент..."
final_response: normal README advice text
tool_results: []
metadata.tool_route: no_tools
```

Conclusion: Qwen/Ollama can emit tool calls when properly bound. The runtime does not bind tools, so the model behaves like a normal chat model.

## Tool Schema Conversion Gap

The internal registry snapshot exposes JSON schemas:

```python
BaseTool.metadata()["input_schema"] = self.input_schema.model_json_schema()
```

But the provider layer does not convert this into either:

- LangChain `BaseTool`/callable/Pydantic tool definitions
- OpenAI-compatible function/tool schema
- Anthropic tool schema
- Ollama-compatible tool binding

## Tool Result Feedback Gap

After a tool executes, `tool_executor_node` writes `tool_results` in state. The next model call passes them only in `ModelRequest.metadata`.

The message history after `read_file` contains:

```text
HumanMessage("tool:read_file ...")
AIMessage("Calling tool read_file")       # no tool_calls persisted on message
AIMessage("Tool read_file ok: hello")     # no ToolMessage
```

This is incompatible with real tool-calling providers, which expect a tool-call AI message followed by corresponding tool-result messages.

## Required Provider Fixes

P0:

1. Add `SystemMessage` with `request.system_context`.
2. Convert registered tools to provider-compatible LangChain tools.
3. Call `bind_tools` for providers that support it.
4. Preserve `AIMessage.tool_calls` in the message state.
5. Add `ToolMessage` or provider-specific tool-result messages after execution.
6. Normalize tool call names/ids/args into `pending_tool_calls`.
7. Add fallback JSON parser/repair for local models when native tool-calling is unavailable or unreliable.
