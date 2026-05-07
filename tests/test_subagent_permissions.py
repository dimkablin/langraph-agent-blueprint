"""Permission safety tests for subagent child graph execution."""

from __future__ import annotations

import json
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_child_write_file_does_not_bypass_permission_when_nested_approval_is_unhandled(tmp_path: Path) -> None:
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    runtime = AssistantGraphRuntime(deps)
    prompt = json.dumps(
        {
            "prompt": 'tool:write_file {"path":"child.txt","content":"secret"}',
            "name": "writer",
            "allowed_tools": ["write_file"],
        }
    )

    result = runtime.invoke(f"tool:agent {prompt}", input_kind="headless", project_root=tmp_path)

    child = result["child_runs"][-1]
    assert child["metadata"]["status"] == "failed"
    assert child["result"]["status"] == "error"
    assert "requires approval" in child["result"]["summary"]
    assert not (tmp_path / "child.txt").exists()

