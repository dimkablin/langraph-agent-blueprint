"""Regression coverage for context compaction state shaping."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from langgraph_agent_blueprint.services.compaction_service import CompactionService


def test_compaction_estimated_tokens_tracks_compacted_messages_not_full_old_transcript() -> None:
    service = CompactionService(keep_recent=1)
    state = {
        "messages": [
            HumanMessage(content="old context " + ("x" * 12000)),
            AIMessage(content="recent answer"),
        ]
    }

    update = service.compact_state(state)

    assert update["context_status"]["estimated_tokens"] == service.estimate_tokens(update["messages"])
    assert update["context_status"]["estimated_tokens"] < service.estimate_tokens(state["messages"])


def test_compaction_preserves_recent_tool_call_result_pair() -> None:
    service = CompactionService(keep_recent=1)
    tool_call = {"id": "call_read", "name": "read_file", "args": {"path": "src/app.py"}}
    state = {
        "messages": [
            HumanMessage(content="older request"),
            AIMessage(content="older response"),
            AIMessage(content="", tool_calls=[tool_call]),
            ToolMessage(content="file contents", tool_call_id="call_read"),
        ]
    }

    update = service.compact_state(state)
    compacted = update["messages"]

    assert isinstance(compacted[0], SystemMessage)
    assert isinstance(compacted[1], AIMessage)
    assert compacted[1].tool_calls[0]["id"] == "call_read"
    assert isinstance(compacted[2], ToolMessage)
    assert compacted[2].tool_call_id == "call_read"
