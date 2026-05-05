"""Runtime-audit regression tests proving end-to-end graph behavior for commands, skills, providers, and tools."""

from __future__ import annotations

import inspect
import platform
import shutil

import pytest
from langchain_core.messages import ToolMessage

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime
from claude_code_langgraph.services import model_provider


def test_default_project_root_is_not_storage_dir(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))

    assert deps.config.project_root != tmp_path.resolve()


def test_tool_events_survive_to_final_state(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )

    result = runtime.invoke('tool:read_file {"path":"README.md"}', input_kind="headless", project_root=tmp_path)
    event_types = [event["type"] for event in result["ui_events"]]

    assert "tool_call_started" in event_types
    assert "tool_call_finished" in event_types
    assert "session_persisted" in event_types


def test_tool_result_is_returned_as_tool_message(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )

    result = runtime.invoke('tool:read_file {"path":"README.md"}', input_kind="headless", project_root=tmp_path)

    assert any(isinstance(message, ToolMessage) for message in result["messages"])


def test_real_provider_path_mentions_system_context_and_bind_tools():
    source = inspect.getsource(model_provider.ModelProviderService)

    assert "SystemMessage" in source
    assert "bind_tools" in source


def test_manual_compact_surfaces_compact_event_not_fake_response(tmp_path):
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )

    result = runtime.invoke("/compact", input_kind="headless", project_root=tmp_path)
    event_types = [event["type"] for event in result["ui_events"]]

    assert "compact_finished" in event_types
    assert not result["final_response"].startswith("Fake response:")


def test_help_command_events_survive_to_final_state(tmp_path):
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )

    result = runtime.invoke("/help", input_kind="headless", project_root=tmp_path)
    event_types = [event["type"] for event in result["ui_events"]]

    assert "command_started" in event_types
    assert "command_finished" in event_types
    assert "final_response" in event_types


def test_permission_resolution_event_survives_after_approval(tmp_path):
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )

    first = runtime.invoke("tool:write_file created.txt hello", input_kind="headless", thread_id="runtime-approval", project_root=tmp_path)
    assert "__interrupt__" in first
    assert any(event["type"] == "permission_required" for event in first["ui_events"])

    result = runtime.resume("runtime-approval", {"approved": True})
    event_types = [event["type"] for event in result["ui_events"]]

    assert "permission_required" in event_types
    assert "permission_resolved" in event_types
    assert "tool_call_finished" in event_types


@pytest.mark.skipif(platform.system() != "Windows" or not shutil.which("rg"), reason="Windows ripgrep parsing issue only")
def test_grep_handles_windows_ripgrep_paths(tmp_path):
    (tmp_path / "notes.txt").write_text("needle\n", encoding="utf-8")
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )

    result = runtime.invoke('tool:grep {"pattern":"needle"}', input_kind="headless", project_root=tmp_path)

    assert result["tool_results"][0]["status"] == "ok"
