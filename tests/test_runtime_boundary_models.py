"""Tests for Pydantic boundary DTOs used at runtime layer edges."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage
from pydantic import ValidationError

from langgraph_agent_blueprint.models.base import dump_model, validate_list
from langgraph_agent_blueprint.models.events import RuntimeEvent, make_event
from langgraph_agent_blueprint.models.tools import ToolCall, ToolResult, normalize_provider_tool_call, tool_result_to_tool_message


def test_runtime_event_is_json_serializable_with_required_boundary_fields():
    event = make_event("tool_call_started", "session_1", node="tool_router", data={"tool_name": "read_file"})

    payload = dump_model(event)
    encoded = json.dumps(payload)

    assert RuntimeEvent.model_validate(json.loads(encoded)).type == "tool_call_started"
    assert payload["session_id"] == "session_1"
    assert payload["node"] == "tool_router"
    assert payload["severity"] == "info"


def test_tool_call_normalizes_openai_style_provider_call():
    raw = {
        "id": "call_1",
        "function": {"name": "read_file", "arguments": '{"path":"README.md"}'},
    }

    call = normalize_provider_tool_call(raw, provider="ollama")

    assert call == ToolCall(id="call_1", name="read_file", args={"path": "README.md"}, provider="ollama", raw=raw)
    assert dump_model(call)["status"] == "pending"


def test_invalid_tool_call_is_rejected_by_model_validation():
    try:
        ToolCall.model_validate({"id": "call_1", "args": {}})
    except ValidationError as exc:
        assert "name" in str(exc)
    else:
        raise AssertionError("ToolCall without a name should fail validation")


def test_tool_result_roundtrip_and_tool_message_conversion():
    result = ToolResult(id="call_1", name="read_file", status="ok", content="hello", metadata={"path": "README.md"})

    payload = dump_model(result)
    restored = ToolResult.model_validate(payload)
    message = tool_result_to_tool_message(restored)

    assert isinstance(message, ToolMessage)
    assert message.tool_call_id == "call_1"
    assert json.loads(message.content)["status"] == "ok"
    assert json.loads(message.content)["metadata"]["path"] == "README.md"


def test_validate_list_validates_each_item_as_boundary_model():
    calls = validate_list(ToolCall, [{"id": "call_1", "name": "grep", "args": {"pattern": "x"}}])

    assert calls == [ToolCall(id="call_1", name="grep", args={"pattern": "x"})]
