"""Security tests for data-only plugin SDK contributions."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.services.plugin_service import PluginService


def test_disabled_plugin_contributes_nothing(tmp_path: Path) -> None:
    plugin = tmp_path / "disabled_plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"disabled_plugin","enabled":false,"commands":[{"name":"x","type":"static_response","response":"x"}]}',
        encoding="utf-8",
    )

    state = PluginService([plugin], storage_dir=tmp_path / "storage").discover()

    assert state["plugins"][0]["enabled"] is False
    assert state["commands"] == []


def test_plugin_context_path_traversal_becomes_warning(tmp_path: Path) -> None:
    plugin = tmp_path / "bad_context_plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"bad_context_plugin","context_providers":[{"name":"bad","kind":"plugin_file","path":"../secret.txt"}]}',
        encoding="utf-8",
    )

    state = PluginService([plugin], storage_dir=tmp_path / "storage").discover()

    assert state["context_providers"] == []
    assert any("path traversal" in warning["error"] for warning in state["context_warnings"])
