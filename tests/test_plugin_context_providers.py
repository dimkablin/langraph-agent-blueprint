"""Plugin context provider contribution tests."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_plugin_context_provider_resolves_with_trust_marker(tmp_path: Path) -> None:
    plugin = tmp_path / "example_plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / "docs").mkdir()
    (plugin / "docs" / "reference.md").write_text("PLUGIN_REFERENCE_MARKER", encoding="utf-8")
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        """
{
  "name": "example_plugin",
  "context_providers": [
    {"name": "reference", "kind": "plugin_file", "path": "docs/reference.md", "description": "Reference docs"}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, plugin_paths=[plugin]))
    )

    result = runtime.invoke("Use @plugin:example_plugin:reference", input_kind="headless", project_root=tmp_path)

    assert any(fragment["trust"] == "plugin_provided" and "PLUGIN_REFERENCE_MARKER" in fragment["content"] for fragment in result["resolved_context"])

