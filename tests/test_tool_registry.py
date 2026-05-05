"""Pytest coverage for tool registry behavior in the Python/LangGraph assistant."""

from claude_code_langgraph.tools.registry import build_core_tool_registry


def test_core_tools_registered_and_schemas_valid():
    registry = build_core_tool_registry()

    for name in ["read_file", "write_file", "edit_file", "notebook_read", "notebook_edit", "glob", "grep", "bash", "powershell", "web_fetch", "web_search", "todo_write", "agent", "skill", "diagnostics"]:
        tool = registry.get(name)
        assert tool.name == name
        assert tool.input_schema.model_json_schema()
        assert tool.output_schema.model_json_schema()

