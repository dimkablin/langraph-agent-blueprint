"""Tests for declarative plugin hook discovery and command visibility."""

from __future__ import annotations

import json
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.services.plugin_service import PluginService


def _write_plugin(root: Path, hooks: list[dict]) -> Path:
    (root / ".codex-plugin").mkdir(parents=True)
    (root / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "hook-plugin", "version": "1.0.0", "hooks": hooks}),
        encoding="utf-8",
    )
    return root


def test_plugin_manifest_declarative_hook_is_registered_and_adds_context(tmp_path: Path) -> None:
    plugin = _write_plugin(
        tmp_path / "hook-plugin",
        [
            {
                "id": "hook-plugin.add_context",
                "point": "pre_context_build",
                "action": "add_system_context",
                "content": "Plugin-provided context.",
                "priority": 50,
            }
        ],
    )
    runtime = AssistantGraphRuntime(
        build_dependencies(
            AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", plugin_paths=[plugin])
        )
    )

    result = runtime.invoke("hello", input_kind="headless", project_root=tmp_path)

    assert "Plugin-provided context." in result["context_status"]["system_context"]
    assert "[plugin hook: hook-plugin.add_context]" in result["context_status"]["system_context"]
    assert any(event["type"] == "hook_finished" and event["data"]["hook_id"] == "hook-plugin.add_context" for event in result["ui_events"])


def test_malformed_plugin_hook_produces_warning_not_crash(tmp_path: Path) -> None:
    plugin = _write_plugin(
        tmp_path / "bad-hook-plugin",
        [{"id": "bad.hook", "point": "not_a_hook_point", "action": "add_system_context", "content": "ignored"}],
    )

    state = PluginService([plugin], tmp_path / "storage", network_enabled=False).discover()

    assert state["plugins"][0]["hooks_count"] == 0
    assert state["hook_warnings"]
    assert "not_a_hook_point" in state["hook_warnings"][0]["error"]


def test_hooks_command_lists_registered_hooks(tmp_path: Path) -> None:
    plugin = _write_plugin(
        tmp_path / "hook-plugin",
        [{"id": "hook-plugin.context", "point": "pre_model", "action": "add_system_context", "content": "Use tests."}],
    )
    runtime = AssistantGraphRuntime(
        build_dependencies(
            AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", plugin_paths=[plugin])
        )
    )

    result = runtime.invoke("/hooks", input_kind="headless", project_root=tmp_path)

    assert "Registered hooks:" in result["final_response"]
    assert "hook-plugin.context" in result["final_response"]
    assert "pre_model" in result["final_response"]

