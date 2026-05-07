"""Subagent context inheritance tests."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.state import create_initial_state
from langgraph_agent_blueprint.models.context import ContextFragment, ContextReference
from langgraph_agent_blueprint.models.subagents import SubagentRequest


def test_child_state_inherits_context_without_sharing_mutable_lists(tmp_path: Path) -> None:
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path))
    parent = create_initial_state("parent", project_root=tmp_path)
    parent["context_references"] = [ContextReference(kind="file", value="README.md").model_dump(mode="json")]
    parent["resolved_context"] = [
        ContextFragment(id="ctx_1", kind="file", title="README.md", content="hello", trust="trusted_local").model_dump(mode="json")
    ]
    request = SubagentRequest(prompt="child", inherit_context=True)

    metadata = deps.agent_service.create_child_metadata(parent, request)
    child = deps.agent_service.create_child_state(parent, request, metadata, deps.tool_registry)

    assert child["context_references"] == parent["context_references"]
    assert child["resolved_context"] == parent["resolved_context"]
    assert child["context_references"] is not parent["context_references"]
    assert child["resolved_context"] is not parent["resolved_context"]
