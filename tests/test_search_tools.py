from claude_code_langgraph.services.search_service import SearchService
from claude_code_langgraph.tools.base import ToolExecutionContext
from claude_code_langgraph.tools.search_tools import GlobInput, GlobTool, GrepInput, GrepTool


def test_glob_works(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("print('x')", encoding="utf-8")
    context = ToolExecutionContext(project_root=tmp_path, cwd=tmp_path)

    result = GlobTool(SearchService()).run(GlobInput(pattern="**/*.py"), context)

    assert any(path.endswith("a.py") for path in result.matches)


def test_grep_works_with_python_fallback(tmp_path):
    target = tmp_path / "a.py"
    target.write_text("needle\n", encoding="utf-8")
    context = ToolExecutionContext(project_root=tmp_path, cwd=tmp_path)

    result = GrepTool(SearchService(force_python=True)).run(GrepInput(pattern="needle"), context)

    assert result.matches[0]["line"] == 1
    assert "needle" in result.matches[0]["text"]

