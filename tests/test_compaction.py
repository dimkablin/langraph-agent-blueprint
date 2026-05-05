"""Pytest coverage for compaction behavior in the Python/LangGraph assistant."""

from langchain_core.messages import HumanMessage

from claude_code_langgraph.services.compaction_service import CompactionService


def test_compaction_creates_summary_and_preserves_recent_messages():
    service = CompactionService(max_messages_before_compact=3)
    messages = [HumanMessage(content=f"message {idx}") for idx in range(6)]
    state = {"messages": messages, "todos": [{"content": "keep me"}], "context_status": {}}

    update = service.compact_state(state)

    assert update["context_status"]["compacted"] is True
    assert "message 0" in update["context_status"]["summary"]
    assert update["todos"] == [{"content": "keep me"}]
    assert update["messages"][-1].content == "message 5"

