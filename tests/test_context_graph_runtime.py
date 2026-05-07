"""Graph integration tests for context references and system context injection."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_prompt_file_reference_is_resolved_and_injected_into_system_context(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("CTX_GRAPH_TOKEN", encoding="utf-8")
    runtime = AssistantGraphRuntime(build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path)))

    result = runtime.invoke("Use @README.md as context", project_root=tmp_path)

    system_context = result["context_status"]["system_context"]
    assert "[Attached file: README.md]" in system_context
    assert "Trust: trusted_local" in system_context
    assert "CTX_GRAPH_TOKEN" in system_context
    assert result["metadata"]["context_references"][0]["value"] == "README.md"
    assert result["metadata"]["context_budget"]["included"]
    event_types = [item["type"] for item in result["ui_events"]]
    assert "context_resolution_started" in event_types
    assert "context_fragment_added" in event_types
    assert "context_budget_applied" in event_types


def test_context_metadata_persists_with_session(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("persisted context", encoding="utf-8")
    runtime = AssistantGraphRuntime(build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path)))

    result = runtime.invoke("Use @README.md", project_root=tmp_path)
    loaded = runtime.dependencies.session_storage.load_session(tmp_path, result["session_id"])

    assert loaded["metadata"]["context_references"][0]["value"] == "README.md"
    assert loaded["metadata"]["context_budget"]["included"]
