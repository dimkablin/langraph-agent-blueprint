"""Runtime-audit regression tests proving end-to-end graph behavior for commands, skills, providers, and tools."""

from __future__ import annotations

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.models.llm import ModelRequest
from langgraph_agent_blueprint.services.model_provider import ModelProviderService


class DummyBindableModel:
    """Minimal bind_tools-capable chat model used to assert provider integration."""

    def __init__(self) -> None:
        self.bound_tools = None
        self.invoked_messages = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.invoked_messages = messages
        return AIMessage(content="", tool_calls=[{"id": "call_1", "name": "read_file", "args": {"path": "README.md"}}])


class DummyStreamingModel(DummyBindableModel):
    """Minimal streaming chat model used to assert token streaming integration."""

    def stream(self, messages):
        self.invoked_messages = messages
        yield AIMessageChunk(content="Hel")
        yield AIMessageChunk(content="lo")


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
                "provider": "ollama",
                "raw": {"name": "read_file", "args": {"path": "README.md"}, "id": "call_1", "type": "tool_call"},
                "status": "pending",
            }
    ]


def test_langchain_provider_streams_tokens_and_returns_final_response(monkeypatch):
    provider = ModelProviderService(AppConfig(llm_provider="ollama", ollama_model="fake"))
    dummy = DummyStreamingModel()
    monkeypatch.setattr(provider, "_build_chat_model", lambda provider_name: dummy)

    stream = list(
        provider.stream_generate(
            ModelRequest(
                system_context="You are a coding assistant.",
                messages=[HumanMessage(content="say hello")],
                tools={
                    "read_file": {
                        "name": "read_file",
                        "description": "Read a file",
                        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
                    }
                },
            )
        )
    )

    assert [event.token for event in stream if event.type == "token"] == ["Hel", "lo"]
    responses = [event.response for event in stream if event.type == "response"]
    assert len(responses) == 1
    assert responses[0].content == "Hello"
    assert isinstance(dummy.invoked_messages[0], SystemMessage)
    assert dummy.bound_tools[0]["function"]["name"] == "read_file"
