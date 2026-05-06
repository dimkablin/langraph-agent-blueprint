"""Project identity tests for the LangGraph Agent Blueprint rename."""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path


def test_python_package_uses_langgraph_agent_blueprint_name():
    module = importlib.import_module("langgraph_agent_blueprint")

    assert module.__name__ == "langgraph_agent_blueprint"


def test_pyproject_exposes_lg_agent_cli_script():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "langgraph-agent-blueprint"
    assert pyproject["project"]["scripts"]["lg-agent"] == "langgraph_agent_blueprint.cli:app"
