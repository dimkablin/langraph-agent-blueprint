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


def test_context_window_overflow_compacts_even_without_old_history() -> None:
    service = CompactionService(
        max_tokens_before_compact=10_000,
        keep_recent=6,
        context_window_max_tokens=120,
    )
    state = {"messages": [HumanMessage(content="current request " + ("x" * 1200))], "available_tools": {}}

    decision = service.compaction_decision(state)
    update = service.compact_state(state)
    pressure = service.context_window_pressure({**state, "messages": update["messages"]})

    assert decision.should_compact is True
    assert decision.reason == "context_window"
    assert pressure is not None
    assert pressure["overflow_tokens"] == 0
    assert update["context_status"]["estimated_tokens"] == service.estimate_tokens(update["messages"])


def test_context_window_compaction_fits_recent_tail_to_message_budget() -> None:
    service = CompactionService(
        max_tokens_before_compact=10_000,
        keep_recent=8,
        context_window_max_tokens=260,
        max_summary_tokens=120,
    )
    messages = [
        HumanMessage(content=f"old user {index} " + ("o" * 700))
        for index in range(5)
    ]
    messages.extend(
        [
            AIMessage(content="recent assistant " + ("a" * 900)),
            HumanMessage(content="latest user " + ("u" * 900)),
        ]
    )
    state = {"messages": messages, "available_tools": {}, "context_status": {"system_context": ""}}

    update = service.compact_state(state)
    pressure = service.context_window_pressure({**state, "messages": update["messages"]})

    assert pressure is not None
    assert pressure["overflow_tokens"] == 0
    assert service.estimate_tokens(update["messages"]) <= pressure["message_budget_tokens"]
    assert service.estimate_tokens(update["messages"]) < service.estimate_tokens(messages)
