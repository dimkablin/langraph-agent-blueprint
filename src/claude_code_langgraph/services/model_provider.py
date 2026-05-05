from __future__ import annotations

import json
import re
import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.models.llm import ModelRequest, ModelResponse
from claude_code_langgraph.models.messages import Usage
from claude_code_langgraph.utils.ids import new_id


class ModelProviderService:
    """Provider abstraction for fake, OpenAI, Ollama, Anthropic, and compatible APIs."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, request: ModelRequest) -> ModelResponse:
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
        text = self._last_human_text(request.messages)
        if request.metadata.get("tool_results"):
            result = request.metadata["tool_results"][-1]
            status = result.get("status", "ok")
            content = result.get("content", "")
            return ModelResponse(content=f"Tool {result.get('name')} {status}: {content}".strip(), usage=self._usage(text))
        tool_call = self._parse_fake_tool_call(text)
        if tool_call:
            return ModelResponse(content=f"Calling tool {tool_call['name']}", tool_calls=[tool_call], usage=self._usage(text))
        return ModelResponse(content=f"Fake response: {text}", usage=self._usage(text))

    def _parse_fake_tool_call(self, text: str) -> dict[str, Any] | None:
        if not text.startswith("tool:"):
            return None
        command = text[5:].strip()
        if command == "fail":
            return {"id": new_id("tool"), "name": "fail", "args": {}}
        if command.startswith("bash "):
            return {"id": new_id("tool"), "name": "bash", "args": {"command": command[5:]}}
        if command.startswith("write_file "):
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
        model = self._build_chat_model(provider)
        messages: list[BaseMessage] = list(request.messages)
        response = model.invoke(messages)
        content = str(getattr(response, "content", ""))
        tool_calls = list(getattr(response, "tool_calls", []) or [])
        return ModelResponse(content=content, tool_calls=tool_calls, raw=response, usage=self._usage(content))

    def _build_chat_model(self, provider: str) -> Any:
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
    def _usage(text: str) -> Usage:
        tokens = max(1, len(text) // 4)
        return Usage(input_tokens=tokens, output_tokens=tokens, total_tokens=tokens * 2)

