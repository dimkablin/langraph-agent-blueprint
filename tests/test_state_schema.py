from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages

from claude_code_langgraph.graph.state import AssistantState, create_initial_state


def test_state_contains_required_defaults(tmp_path):
    state: AssistantState = create_initial_state("hello", project_root=tmp_path)

    assert state["session_id"]
    assert state["thread_id"]
    assert state["project_root"] == str(tmp_path)
    assert state["input_text"] == "hello"
    assert state["pending_confirmation"] is None
    assert state["messages"] == []


def test_messages_append_with_langgraph_add_messages():
    first = [HumanMessage(content="one")]
    second = [HumanMessage(content="two")]

    merged = add_messages(first, second)

    assert [message.content for message in merged] == ["one", "two"]

