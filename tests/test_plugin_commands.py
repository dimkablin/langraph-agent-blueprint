"""Plugin command contribution runtime tests."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def _write_plugin(root: Path) -> Path:
    plugin = root / "example_plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / "skills" / "example-skill").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        """
{
  "name": "example_plugin",
  "skills": "./skills",
  "commands": [
    {"name": "hello", "type": "static_response", "response": "Hello from plugin"},
    {"name": "ask", "type": "prompt", "prompt": "Plugin prompt: {args}"},
    {"name": "do_skill", "type": "skill", "skill": "example_plugin/example-skill"}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    (plugin / "skills" / "example-skill" / "SKILL.md").write_text("Plugin skill says {{args}}", encoding="utf-8")
    return plugin


def test_plugin_static_prompt_and_skill_commands_work_without_graph_edits(tmp_path: Path) -> None:
    plugin = _write_plugin(tmp_path)
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, plugin_paths=[plugin]))
    )

    static_result = runtime.invoke("/hello", input_kind="headless", project_root=tmp_path)
    prompt_result = runtime.invoke("/ask something", input_kind="headless", project_root=tmp_path)
    skill_result = runtime.invoke("/do_skill work", input_kind="headless", project_root=tmp_path)

    assert static_result["final_response"] == "Hello from plugin"
    assert "Plugin prompt: something" in prompt_result["final_response"]
    assert any(event["type"] == "skill_started" and event["data"]["name"] == "example_plugin/example-skill" for event in skill_result["ui_events"])

