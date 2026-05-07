"""Regression tests for generic plugin policy contributions."""

from __future__ import annotations

import json
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.plugins import PluginPolicyContribution, PluginPolicyContext
from langgraph_agent_blueprint.plugins.policy import evaluate_plugin_policy_contributions


def _write_policy_plugin(root: Path, *, priority: int = 50, enabled: bool = True, skill_name: str = "policy-plugin/example-skill") -> Path:
    (root / ".codex-plugin").mkdir(parents=True)
    (root / "skills" / "example-skill").mkdir(parents=True)
    (root / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "name": "policy-plugin",
                "skills": "./skills",
                "policies": [
                    {
                        "id": "policy-plugin.activate_example",
                        "type": "skill_activation",
                        "priority": priority,
                        "enabled": enabled,
                        "skill": skill_name,
                        "match_any": ["trigger fake policy"],
                        "reason": "fake plugin policy matched",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "skills" / "example-skill" / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: fake policy skill\n---\nFake policy skill: {{args}}\n",
        encoding="utf-8",
    )
    return root


def test_fake_plugin_policy_activates_skill_without_graph_code_change(tmp_path: Path) -> None:
    plugin = _write_policy_plugin(tmp_path / "policy-plugin")
    runtime = AssistantGraphRuntime(
        build_dependencies(
            AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", plugin_paths=[plugin])
        )
    )

    result = runtime.invoke("please trigger fake policy", input_kind="headless", project_root=tmp_path)

    assert result["active_skill"]["name"] == "policy-plugin/example-skill"
    assert any(event["type"] == "plugin_policy_applied" for event in result["ui_events"])


def test_plugin_policy_priorities_and_disabled_flags_are_honored() -> None:
    disabled = PluginPolicyContribution(
        id="disabled",
        plugin_name="fake",
        priority=1,
        enabled=False,
        metadata={"rules": [{"skill_name": "fake/disabled", "match_any": ["work"]}]},
    )
    lower_priority = PluginPolicyContribution(
        id="low",
        plugin_name="fake",
        priority=200,
        metadata={"rules": [{"skill_name": "fake/low", "match_any": ["work"]}]},
    )
    higher_priority = PluginPolicyContribution(
        id="high",
        plugin_name="fake",
        priority=10,
        metadata={"rules": [{"skill_name": "fake/high", "match_any": ["work"]}]},
    )
    context = PluginPolicyContext(session_id="session", input_text="work on this")

    results = evaluate_plugin_policy_contributions([disabled, lower_priority, higher_priority], context)

    assert results[0].action == "activate_skill"
    assert results[0].skill_name == "fake/high"


def test_plugin_policy_errors_are_structured_not_exceptions() -> None:
    contribution = PluginPolicyContribution(
        id="bad",
        plugin_name="fake",
        metadata={"rules": [{"match_any": ["work"]}]},
    )
    context = PluginPolicyContext(session_id="session", input_text="work on this")

    results = evaluate_plugin_policy_contributions([contribution], context)

    assert results[0].action == "error"
    assert "skill_name" in str(results[0].reason)
