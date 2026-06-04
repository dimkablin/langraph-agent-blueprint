"""Behavioral tests for frontend-safe session message and context serialization."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from langgraph_agent_blueprint.api.serializers import context_state_dto, message_dtos


def test_message_dtos_hide_tool_result_messages_from_chat_history() -> None:
    messages = [
        HumanMessage(content="what is in the folder?"),
        AIMessage(content="", tool_calls=[{"id": "call_glob", "name": "glob", "args": {"pattern": "*"}}]),
        ToolMessage(
            content='{"name":"glob","status":"ok","content":"C:\\\\project\\\\README.md"}',
            tool_call_id="call_glob",
        ),
        AIMessage(content="The project folder contains README.md."),
    ]

    serialized = message_dtos(messages)

    assert [message.role for message in serialized] == ["human", "ai"]
    assert [message.content for message in serialized] == [
        "what is in the folder?",
        "The project folder contains README.md.",
    ]


def test_context_state_dto_exposes_persisted_model_context_report() -> None:
    snapshot = {
        "metadata": {
            "model_context": {
                "max_tokens": 1000,
                "used_tokens": 120,
                "remaining_tokens": 880,
                "percent": 12,
                "truncated": False,
                "parts": [{"kind": "messages", "title": "Message 1", "content": "current question"}],
            }
        }
    }

    dto = context_state_dto(snapshot)

    assert dto.model_context["used_tokens"] == 120
    assert dto.model_context["parts"][0]["content"] == "current question"
