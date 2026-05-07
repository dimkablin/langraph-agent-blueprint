"""File and notebook context provider coverage."""

from __future__ import annotations

import json
from pathlib import Path

from langgraph_agent_blueprint.context.providers import ContextProviderService
from langgraph_agent_blueprint.models.context import ContextReference


def test_file_provider_reads_safe_text_file_with_relative_title(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("CTX_TOKEN file payload", encoding="utf-8")
    service = ContextProviderService(project_root=tmp_path, max_file_bytes=200)

    item = service.resolve(ContextReference(kind="file", value="README.md"))

    assert not item.errors
    fragment = item.fragments[0]
    assert fragment.title == "README.md"
    assert fragment.trust == "trusted_local"
    assert "CTX_TOKEN" in fragment.content
    assert str(tmp_path) not in fragment.title


def test_file_provider_rejects_path_traversal(tmp_path: Path) -> None:
    service = ContextProviderService(project_root=tmp_path)

    item = service.resolve(ContextReference(kind="file", value="../secret.txt"))

    assert item.errors
    assert item.fragments == []
    assert "outside allowed root" in item.errors[0]["message"]


def test_notebook_provider_returns_cell_summary_without_execution(tmp_path: Path) -> None:
    notebook = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title\n"]},
            {"cell_type": "code", "source": ["print('CTX_NOTEBOOK')\n"]},
        ],
        "metadata": {"kernelspec": {"name": "python3"}},
    }
    (tmp_path / "analysis.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    service = ContextProviderService(project_root=tmp_path)

    item = service.resolve(ContextReference(kind="notebook", value="analysis.ipynb"))

    assert not item.errors
    assert "CTX_NOTEBOOK" in item.fragments[0].content
    assert "Notebook cells" in item.fragments[0].content
