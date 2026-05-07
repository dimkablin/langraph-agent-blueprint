"""Directory and glob context provider coverage."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.context.providers import ContextProviderService
from langgraph_agent_blueprint.models.context import ContextReference


def test_directory_provider_lists_tree_summary_without_file_contents(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("SECRET_CONTENT", encoding="utf-8")
    (src / "b.py").write_text("print('b')", encoding="utf-8")
    service = ContextProviderService(project_root=tmp_path, max_directory_files=10)

    item = service.resolve(ContextReference(kind="directory", value="src/"))

    content = item.fragments[0].content
    assert "src/a.py" in content
    assert "src/b.py" in content
    assert "SECRET_CONTENT" not in content


def test_glob_provider_returns_limited_file_list(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for name in ["a.py", "b.py", "c.txt"]:
        (src / name).write_text(name, encoding="utf-8")
    service = ContextProviderService(project_root=tmp_path, max_glob_files=1)

    item = service.resolve(ContextReference(kind="glob", value="src/*.py"))

    content = item.fragments[0].content
    assert content.count(".py") == 1
    assert item.fragments[0].truncated is True
