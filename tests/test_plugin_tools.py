"""Plugin tool contribution runtime tests."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def test_plugin_static_tool_registers_and_executes_through_graph(tmp_path: Path) -> None:
    plugin = tmp_path / "example_plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        """
{
  "name": "example_plugin",
  "tools": [
    {"name": "static_hello", "kind": "static_text", "description": "Static hello", "response": "hello from plugin tool"}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, plugin_paths=[plugin]))
    runtime = AssistantGraphRuntime(deps)

    result = runtime.invoke('tool:plugin.example_plugin.static_hello {"value":"ignored"}', input_kind="headless", project_root=tmp_path)

    assert "plugin.example_plugin.static_hello" in deps.tool_registry.snapshot()
    assert result["tool_results"][-1]["status"] == "ok"
    assert "hello from plugin tool" in result["final_response"]

