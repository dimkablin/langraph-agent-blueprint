"""Behavioral tests for frontend-safe session message serialization."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from langgraph_agent_blueprint.api.serializers import message_dtos


def test_message_dtos_hide_tool_result_messages_from_chat_history() -> None:
    messages = [
        HumanMessage(content="привет что в папке?"),
        AIMessage(content="", tool_calls=[{"id": "call_glob", "name": "glob", "args": {"pattern": "*"}}]),
        ToolMessage(
            content='{"name":"glob","status":"ok","content":"C:\\\\project\\\\README.md"}',
            tool_call_id="call_glob",
        ),
        AIMessage(content="В папке проекта находится README.md."),
    ]

    serialized = message_dtos(messages)

    assert [message.role for message in serialized] == ["human", "ai"]
    assert [message.content for message in serialized] == [
        "привет что в папке?",
        "В папке проекта находится README.md.",
    ]
