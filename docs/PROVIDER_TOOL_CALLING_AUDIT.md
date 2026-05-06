# Provider Tool Calling Audit

Current acceptance status as of 2026-05-06.

## Provider Matrix

| Provider | SystemMessage passed | Tools bound | Tool calls parsed | ToolMessage feedback | Streaming/events | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fake` | request contract uses system context | deterministic fake tool calls | yes | yes | graph UI events | `working` | Regression tests prove `AIMessage.tool_calls`, ToolMessage feedback, and final response. |
| `ollama` | yes | yes via `ChatOllama.bind_tools` | yes | yes | graph UI events | `working` for tested `qwen3:14b` | Live smoke emitted `read_file` call, ToolMessage, and final answer `ACCEPTANCE_README_LINE`. |
| `openai_compatible` | yes | yes through LangChain `ChatOpenAI` compatible config | provider dependent | yes when provider returns tool calls | graph UI events | `working_with_provider_requirement` | Code path shares `_langchain_generate`; not live-tested without configured endpoint. |
| `openai` | yes | yes through LangChain `ChatOpenAI` | provider dependent | yes when provider returns tool calls | graph UI events | `working_with_provider_requirement` | Code path shares `_langchain_generate`; tests mock bind-tools contract without cloud keys. |
| `anthropic` | yes | yes through LangChain `ChatAnthropic` when installed | provider dependent | yes when provider returns tool calls | graph UI events | `working_with_provider_requirement` | Optional dependency; not required by CI. |

## Ollama Acceptance Evidence

Environment:

```text
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:14b
OLLAMA_BASE_URL=http://localhost:11434
```

Prompt:

```text
Use the read_file tool to read README.md. Do not answer from memory. After the tool result, answer with the first line only.
```

Observed:

- `AIMessage.tool_calls`: `read_file` with args `{"path": "README.md"}`
- `ToolMessage.tool_call_id`: matched the provider tool call id
- ToolMessage content included `ACCEPTANCE_README_LINE`
- final response: `ACCEPTANCE_README_LINE`
- event types included `tool_call_started`, `tool_call_finished`, `session_persisted`, `final_response`

## Tool Schema Conversion

`ModelProviderService._langchain_tool_schemas` converts registry metadata to LangChain/OpenAI-style function schemas while preserving registry names such as `read_file`, `write_file`, `grep`, `bash`, `powershell`, `skill`, and `todo_write`.

## Fallback Behavior

If a local model returns JSON-like tool calls as text instead of native tool calls, `_parse_json_tool_calls` attempts bounded parsing. If no provider tool call or parseable fallback exists, the model response is treated as normal text instead of pretending that tools were called.

## Historical Audit Result

Before the fixes, real providers received ordinary messages without `SystemMessage` insertion or `bind_tools`, so Ollama/Qwen answered as if tools did not exist. That result is historical only.
