"""Provider abstraction that adapts fake, Ollama, OpenAI-compatible, OpenAI, and Anthropic chat models."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.models.base import dump_model
from claude_code_langgraph.models.llm import ModelRequest, ModelResponse
from claude_code_langgraph.models.messages import Usage
from claude_code_langgraph.models.tools import ToolCall, normalize_provider_tool_calls
from claude_code_langgraph.utils.ids import new_id


class ModelProviderService:
    """Provider abstraction for fake, OpenAI, Ollama, Anthropic, and compatible APIs."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Dispatch a provider-agnostic request to the configured chat provider and attach usage."""

        start = time.perf_counter()
        if self.config.llm_provider == "fake":
            response = self._fake_generate(request)
        elif self.config.llm_provider == "ollama":
            response = self._langchain_generate(request, "ollama")
        elif self.config.llm_provider == "openai":
            response = self._langchain_generate(request, "openai")
        elif self.config.llm_provider == "openai_compatible":
            response = self._langchain_generate(request, "openai_compatible")
        elif self.config.llm_provider == "anthropic":
            response = self._langchain_generate(request, "anthropic")
        else:
            raise ValueError(f"Unsupported provider: {self.config.llm_provider}")
        response.usage.duration_ms = (time.perf_counter() - start) * 1000
        response.usage.provider = self.config.llm_provider
        response.usage.model = self.config.effective_model()
        return response

    def _fake_generate(self, request: ModelRequest) -> ModelResponse:
        """Implement deterministic fake-provider behavior for tests and local smoke runs."""

        text = self._last_human_text(request.messages)
        if request.metadata.get("tool_results") or self._last_message_is_tool_result(request.messages):
            result = (request.metadata.get("tool_results") or [{"name": "tool", "status": "ok", "content": str(request.messages[-1].content)}])[-1]
            status = result.get("status", "ok")
            content = result.get("content", "")
            response_text = f"Tool {result.get('name')} {status}: {content}".strip()
            return ModelResponse(content=response_text, raw=AIMessage(content=response_text), usage=self._usage(text))
        tool_call = self._parse_fake_tool_call(text)
        if tool_call:
            call = ToolCall.model_validate({**tool_call, "provider": "fake"})
            content = f"Calling tool {call.name}"
            message = AIMessage(content=content, tool_calls=[self._ai_message_tool_call(call)])
            return ModelResponse(content=content, tool_calls=[dump_model(call)], raw=message, usage=self._usage(text))
        response_text = f"Fake response: {text}"
        return ModelResponse(content=response_text, raw=AIMessage(content=response_text), usage=self._usage(text))

    def _parse_fake_tool_call(self, text: str) -> dict[str, Any] | None:
        """Parse `tool:<name> ...` fake prompts into normalized tool-call dictionaries."""

        if not text.startswith("tool:"):
            return None
        command = text[5:].strip()
        if command == "fail":
            return {"id": new_id("tool"), "name": "fail", "args": {}}
        if command.startswith("bash "):
            rest = command[5:].strip()
            if rest.startswith("{"):
                try:
                    args = json.loads(rest)
                except json.JSONDecodeError:
                    args = {"command": rest}
                return {"id": new_id("tool"), "name": "bash", "args": args if isinstance(args, dict) else {"command": rest}}
            return {"id": new_id("tool"), "name": "bash", "args": {"command": rest}}
        if command.startswith("write_file ") and not command[len("write_file ") :].lstrip().startswith("{"):
            parts = command.split(" ", 2)
            content = parts[2] if len(parts) > 2 else ""
            return {"id": new_id("tool"), "name": "write_file", "args": {"path": parts[1], "content": content}}
        if command.startswith("agent "):
            return {"id": new_id("tool"), "name": "agent", "args": {"prompt": command[6:]}}
        match = re.match(r"(\w+)(?:\s+(.+))?", command)
        if match:
            args: dict[str, Any] = {}
            if match.group(2):
                try:
                    args = json.loads(match.group(2))
                except json.JSONDecodeError:
                    args = {"value": match.group(2)}
            return {"id": new_id("tool"), "name": match.group(1), "args": args}
        return None

    def _langchain_generate(self, request: ModelRequest, provider: str) -> ModelResponse:
        """Invoke a LangChain chat model with system context and bound tool schemas."""

        model = self._build_chat_model(provider)
        messages = self._messages_with_system(request)
        tools = self._langchain_tool_schemas(request.tools)
        bound_model = model
        if tools and hasattr(model, "bind_tools"):
            bound_model = model.bind_tools(tools)
        response = bound_model.invoke(messages)
        content = str(getattr(response, "content", ""))
        tool_calls = [dump_model(call) for call in normalize_provider_tool_calls(list(getattr(response, "tool_calls", []) or []), provider)]
        if not tool_calls:
            tool_calls = self._parse_json_tool_calls(content, provider)
        return ModelResponse(content=content, tool_calls=tool_calls, raw=response, usage=self._usage(content))

    @staticmethod
    def _messages_with_system(request: ModelRequest) -> list[BaseMessage]:
        """Prepend request system context unless the message list already contains a SystemMessage."""

        messages: list[BaseMessage] = list(request.messages)
        if request.system_context and not any(isinstance(message, SystemMessage) for message in messages):
            return [SystemMessage(content=request.system_context), *messages]
        return messages

    @staticmethod
    def _langchain_tool_schemas(tools: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert internal ToolRegistry metadata into LangChain/OpenAI-style tool schemas."""

        schemas: list[dict[str, Any]] = []
        for name, metadata in sorted(tools.items()):
            input_schema = metadata.get("input_schema") or {"type": "object", "properties": {}}
            if not isinstance(input_schema, dict):
                input_schema = {"type": "object", "properties": {}}
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": str(metadata.get("description") or ""),
                        "parameters": input_schema,
                    },
                }
            )
        return schemas

    @staticmethod
    def _normalize_tool_calls(tool_calls: list[Any]) -> list[dict[str, Any]]:
        """Normalize provider-specific tool-call shapes into the graph's pending-call schema."""

        return [dump_model(call) for call in normalize_provider_tool_calls(tool_calls)]

    def _parse_json_tool_calls(self, content: str, provider: str = "unknown") -> list[dict[str, Any]]:
        """Fallback parser for local models that emit JSON tool calls as message text."""

        stripped = content.strip()
        if not stripped:
            return []
        candidates = [stripped]
        fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
        if fenced:
            candidates.insert(0, fenced.group(1).strip())
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            raw_calls = parsed.get("tool_calls") if isinstance(parsed, dict) else parsed
            if isinstance(raw_calls, dict):
                raw_calls = [raw_calls]
            if isinstance(raw_calls, list):
                return [dump_model(call) for call in normalize_provider_tool_calls(raw_calls, provider)]
        return []

    @staticmethod
    def _ai_message_tool_call(call: ToolCall) -> dict[str, Any]:
        """Return the subset of ToolCall fields accepted by LangChain AIMessage."""

        return {"id": call.id, "name": call.name, "args": call.args}

    def _build_chat_model(self, provider: str) -> Any:
        """Construct the concrete LangChain chat model for the requested provider name."""

        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(model=self.config.ollama_model, base_url=self.config.ollama_base_url)
        if provider in {"openai", "openai_compatible"}:
            from langchain_openai import ChatOpenAI

            kwargs: dict[str, Any] = {"model": self.config.openai_model or self.config.model_name}
            if provider == "openai_compatible":
                kwargs["base_url"] = self.config.openai_compatible_base_url
                kwargs["api_key"] = self.config.openai_compatible_api_key or "not-needed"
                kwargs["model"] = self.config.openai_compatible_model or self.config.model_name
            elif self.config.openai_api_key:
                kwargs["api_key"] = self.config.openai_api_key
            return ChatOpenAI(**kwargs)
        if provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError as exc:
                raise RuntimeError("langchain-anthropic is not installed") from exc
            return ChatAnthropic(model=self.config.anthropic_model or self.config.model_name, api_key=self.config.anthropic_api_key)
        raise ValueError(provider)

    @staticmethod
    def _last_human_text(messages: list[Any]) -> str:
        for message in reversed(messages):
            if getattr(message, "type", "") == "human" or message.__class__.__name__ == "HumanMessage":
                return str(getattr(message, "content", ""))
        return ""

    @staticmethod
    def _last_message_is_tool_result(messages: list[Any]) -> bool:
        return bool(messages and isinstance(messages[-1], ToolMessage))

    @staticmethod
    def _usage(text: str) -> Usage:
        tokens = max(1, len(text) // 4)
        return Usage(input_tokens=tokens, output_tokens=tokens, total_tokens=tokens * 2)
