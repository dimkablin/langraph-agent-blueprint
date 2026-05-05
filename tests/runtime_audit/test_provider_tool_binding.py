from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.models.llm import ModelRequest
from claude_code_langgraph.services.model_provider import ModelProviderService


class DummyBindableModel:
    def __init__(self) -> None:
        self.bound_tools = None
        self.invoked_messages = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.invoked_messages = messages
        return AIMessage(content="", tool_calls=[{"id": "call_1", "name": "read_file", "args": {"path": "README.md"}}])


def test_langchain_provider_receives_system_context_and_bound_tools(monkeypatch):
    provider = ModelProviderService(AppConfig(llm_provider="ollama", ollama_model="fake"))
    dummy = DummyBindableModel()
    monkeypatch.setattr(provider, "_build_chat_model", lambda provider_name: dummy)

    response = provider._langchain_generate(
        ModelRequest(
            system_context="You are a coding assistant.",
            messages=[HumanMessage(content="read it")],
            tools={
                "read_file": {
                    "name": "read_file",
                    "description": "Read a file",
                    "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
                }
            },
        ),
        "ollama",
    )

    assert isinstance(dummy.invoked_messages[0], SystemMessage)
    assert dummy.invoked_messages[0].content == "You are a coding assistant."
    assert dummy.bound_tools[0]["function"]["name"] == "read_file"
    assert response.tool_calls == [
        {
            "id": "call_1",
            "name": "read_file",
            "args": {"path": "README.md"},
            "raw": {"name": "read_file", "args": {"path": "README.md"}, "id": "call_1", "type": "tool_call"},
            "status": "pending",
        }
    ]
