"""Pytest coverage for export behavior in the Python/LangGraph assistant."""

from langchain_core.messages import AIMessage, HumanMessage

from langgraph_agent_blueprint.services.export_service import ExportService


def test_transcript_export_produces_file_and_text(tmp_path):
    service = ExportService(tmp_path)
    messages = [HumanMessage(content="hi"), AIMessage(content="hello")]

    result = service.export_transcript("s1", messages, format="markdown")

    assert result.path.exists()
    assert "User: hi" in result.text
    assert "Assistant: hello" in result.text

