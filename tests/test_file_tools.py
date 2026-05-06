"""Pytest coverage for file tools behavior in the Python/LangGraph assistant."""

import pytest

from langgraph_agent_blueprint.services.file_service import FileService
from langgraph_agent_blueprint.tools.file_tools import FileEditInput, FileReadInput, FileReadTool, FileWriteInput, FileWriteTool, FileEditTool
from langgraph_agent_blueprint.tools.base import ToolExecutionContext


def test_read_file_works(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("hello\nworld\n", encoding="utf-8")
    context = ToolExecutionContext(project_root=tmp_path, cwd=tmp_path)

    result = FileReadTool(FileService(tmp_path)).run(FileReadInput(path=str(target)), context)

    assert "hello" in result.content
    assert str(target.resolve()) in context.read_files


def test_write_file_requires_permission():
    assert FileWriteTool(FileService(".")).requires_permission is True


def test_edit_requires_permission_and_prior_read(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("hello", encoding="utf-8")
    context = ToolExecutionContext(project_root=tmp_path, cwd=tmp_path)
    tool = FileEditTool(FileService(tmp_path))

    assert tool.requires_permission is True
    with pytest.raises(PermissionError):
        tool.run(FileEditInput(path=str(target), old_text="hello", new_text="bye"), context)

    context.read_files.add(str(target.resolve()))
    result = tool.run(FileEditInput(path=str(target), old_text="hello", new_text="bye"), context)
    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "bye"

