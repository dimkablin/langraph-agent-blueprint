"""Regression coverage for project-local prompt-driven code skill loading."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def _write_code_prompt_project(root: Path) -> None:
    (root / "skills" / "code-prompt").mkdir(parents=True)
    (root / "skills" / "code-prompt" / "SKILL.md").write_text(
        "---\nname: code-prompt\ndescription: Project programming prompt\n---\nCode prompt active: {{args}}\n",
        encoding="utf-8",
    )


def test_relative_project_skills_path_loads_prompt_driven_code_prompt(tmp_path: Path) -> None:
    _write_code_prompt_project(tmp_path)
    config = AppConfig(
        storage_dir=tmp_path / "storage",
        project_root=tmp_path,
        cwd=tmp_path,
        llm_provider="fake",
        skills_paths=[Path("skills")],
    )
    runtime = AssistantGraphRuntime(build_dependencies(config))

    result = runtime.invoke("/skill code-prompt implement a FastAPI endpoint", input_kind="headless", project_root=tmp_path)

    assert result["active_skill"]["name"] == "code-prompt"
    assert "code-prompt" in result["available_skills"]
    assert not any(event["type"] == "plugin_policy_applied" for event in result["ui_events"])
    assert "Code prompt active: implement a FastAPI endpoint" in result["final_response"]
