"""Tests for external Superpowers plugin discovery, bootstrap, and graph policy activation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from langchain_core.messages import ToolMessage

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.graph.nodes.tool_router import tool_router_node
from langgraph_agent_blueprint.graph.state import create_initial_state
from langgraph_agent_blueprint.services.plugin_service import PluginService
from langgraph_agent_blueprint.graph.nodes import plugin_policy as plugin_policy_module


FIXTURE = Path(__file__).parent / "fixtures" / "plugins" / "superpowers"


def _event_has_skill(event: dict, event_type: str, skill_name: str) -> bool:
    return event.get("type") == event_type and event.get("data", {}).get("name") == skill_name


def _runtime(tmp_path: Path, plugin_paths: list[Path] | None = None) -> AssistantGraphRuntime:
    config = AppConfig(
        storage_dir=tmp_path / "storage",
        project_root=tmp_path,
        cwd=tmp_path,
        llm_provider="fake",
        plugin_paths=plugin_paths or [],
    )
    return AssistantGraphRuntime(build_dependencies(config))


def test_superpowers_manifest_detection_reads_codex_manifest_and_bootstrap(tmp_path):
    service = PluginService([], tmp_path / "storage", network_enabled=False)

    contribution = service.discover_contribution(FIXTURE)

    assert contribution.plugin_name == "superpowers"
    assert contribution.manifest.version == "5.1.0"
    assert contribution.manifest.skills_path == "./skills/"
    assert contribution.skills_path == str((FIXTURE / "skills").resolve())
    assert contribution.bootstrap_skill == "using-superpowers"
    assert contribution.system_context_fragments
    assert contribution.policies
    assert contribution.policies[0].id == "superpowers.default_methodology_policy"


def test_plugin_policy_node_does_not_import_superpowers_directly():
    assert "superpowers" not in plugin_policy_module.__dict__


def test_superpowers_manifest_detection_falls_back_to_claude_manifest_and_skills_dir(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".claude-plugin").mkdir(parents=True)
    (repo / "skills" / "using-superpowers").mkdir(parents=True)
    (repo / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "superpowers", "version": "5.1.0", "license": "MIT"}),
        encoding="utf-8",
    )
    (repo / "skills" / "using-superpowers" / "SKILL.md").write_text(
        "---\nname: using-superpowers\ndescription: bootstrap\n---\nBootstrap\n",
        encoding="utf-8",
    )

    contribution = PluginService([], tmp_path / "storage", network_enabled=False).discover_contribution(repo)

    assert contribution.plugin_name == "superpowers"
    assert contribution.skills_path == str((repo / "skills").resolve())
    assert contribution.bootstrap_skill == "using-superpowers"


def test_plugin_skills_load_with_superpowers_namespace_and_metadata(tmp_path):
    deps = build_dependencies(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            llm_provider="fake",
            plugin_paths=[FIXTURE],
        )
    )

    skill = deps.skill_registry.get("superpowers/brainstorming")

    assert deps.skill_registry.get("superpowers/using-superpowers").metadata.plugin_name == "superpowers"
    assert deps.skill_registry.get("superpowers/test-driven-development").metadata.original_name == "test-driven-development"
    assert skill.metadata.name == "superpowers/brainstorming"
    assert skill.metadata.original_name == "brainstorming"
    assert skill.source_path == FIXTURE / "skills" / "brainstorming" / "SKILL.md"
    assert deps.skill_registry.get("brainstorming").metadata.name == "superpowers/brainstorming"


def test_skills_command_lists_plugin_skills_separately(tmp_path):
    result = _runtime(tmp_path, [FIXTURE]).invoke("/skills", input_kind="headless", project_root=tmp_path)

    assert "Built-in skills:" in result["final_response"]
    assert "Plugin skills:" in result["final_response"]
    assert "superpowers/brainstorming" in result["final_response"]


def test_explicit_superpowers_skill_invocation_enters_skill_graph_and_persists(tmp_path):
    runtime = _runtime(tmp_path, [FIXTURE])

    result = runtime.invoke("/skill superpowers/brainstorming build a todo app", input_kind="headless", project_root=tmp_path, session_id="sp-session")
    loaded = runtime.dependencies.session_storage.load_session(tmp_path, "sp-session")

    assert result["active_skill"]["name"] == "superpowers/brainstorming"
    assert any(_event_has_skill(event, "skill_started", "superpowers/brainstorming") for event in result["ui_events"])
    assert "superpowers/brainstorming" in loaded["metadata"]["skill_invocations"]


def test_skill_tool_invokes_namespaced_superpowers_skill(tmp_path):
    result = _runtime(tmp_path, [FIXTURE]).invoke(
        'tool:skill {"skill":"superpowers/brainstorming","args":"feature idea"}',
        input_kind="headless",
        project_root=tmp_path,
    )

    assert result["active_skill"]["name"] == "superpowers/brainstorming"
    assert any(isinstance(message, ToolMessage) for message in result["messages"])


def test_superpowers_bootstrap_context_is_injected_only_when_enabled(tmp_path):
    enabled = _runtime(tmp_path, [FIXTURE]).invoke("hello", input_kind="headless", project_root=tmp_path)
    disabled = _runtime(tmp_path / "disabled", []).invoke("hello", input_kind="headless", project_root=tmp_path / "disabled")

    assert "Superpowers plugin is enabled." in enabled["context_status"]["system_context"]
    assert "superpowers/using-superpowers" in enabled["context_status"]["system_context"]
    assert "Superpowers plugin is enabled." not in disabled["context_status"]["system_context"]


def test_acceptance_react_todo_prompt_auto_activates_brainstorming_before_code(tmp_path):
    result = _runtime(tmp_path, [FIXTURE]).invoke("Let's make a react todo list", input_kind="headless", project_root=tmp_path, session_id="acceptance")

    assert result["active_skill"]["name"] == "superpowers/brainstorming"
    assert any(_event_has_skill(event, "skill_started", "superpowers/brainstorming") for event in result["ui_events"])
    assert any(event["type"] == "plugin_policy_applied" for event in result["ui_events"])
    assert "```" not in result["final_response"]


def test_debug_prompt_auto_activates_systematic_debugging(tmp_path):
    result = _runtime(tmp_path, [FIXTURE]).invoke("Fix this failing test", input_kind="headless", project_root=tmp_path, session_id="debug")

    assert result["active_skill"]["name"] == "superpowers/systematic-debugging"
    assert any(_event_has_skill(event, "skill_started", "superpowers/systematic-debugging") for event in result["ui_events"])


def test_superpowers_policy_does_not_repeat_brainstorming_after_session_invocation(tmp_path):
    runtime = _runtime(tmp_path, [FIXTURE])

    runtime.invoke("Let's make a react todo list", input_kind="headless", project_root=tmp_path, session_id="repeat")
    result = runtime.invoke("Add filtering too", input_kind="headless", project_root=tmp_path, session_id="repeat")

    assert not any(_event_has_skill(event, "skill_started", "superpowers/brainstorming") for event in result["ui_events"])


def test_plugin_discovery_rejects_path_traversal_skills_path(tmp_path):
    repo = tmp_path / "bad-plugin"
    (repo / ".codex-plugin").mkdir(parents=True)
    (repo / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "bad", "skills": "../outside"}),
        encoding="utf-8",
    )

    state = PluginService([repo], tmp_path / "storage", network_enabled=False).discover()

    assert state["errors"]
    assert "path traversal" in state["errors"][0]["error"]


def test_plugin_skill_scope_cannot_bypass_tool_permissions(tmp_path):
    deps = build_dependencies(
        AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", plugin_paths=[FIXTURE])
    )
    state = create_initial_state("call", project_root=tmp_path)
    state["metadata"] = {"allowed_tools_override": ["read_file"]}
    state["pending_tool_calls"] = [{"id": "call_1", "name": "write_file", "args": {"path": "x.txt", "content": "x"}}]

    update = tool_router_node(state, deps)

    assert update["tool_results"][0]["status"] == "rejected"
    assert update["tool_results"][0]["metadata"]["reason"] == "disallowed_by_skill"


def test_git_install_reports_disabled_when_network_is_disabled(tmp_path):
    result = PluginService([], tmp_path / "storage", network_enabled=False).install(
        "superpowers@git+https://github.com/obra/superpowers.git#v5.1.0"
    )

    assert result.status == "error"
    assert "Network access is disabled" in result.message


def test_git_install_timeout_returns_structured_error(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, *, check, text, capture_output, timeout):
        calls.append({"args": args, "timeout": timeout})
        raise subprocess.TimeoutExpired(args, timeout)

    monkeypatch.setattr("langgraph_agent_blueprint.services.plugin_service.subprocess.run", fake_run)

    result = PluginService([], tmp_path / "storage", network_enabled=True, git_timeout_seconds=0.01).install(
        "superpowers@git+https://github.com/obra/superpowers.git#v5.1.0"
    )

    assert result.status == "error"
    assert "timed out" in result.message.lower()
    assert "clone" in result.message.lower()
    assert calls[0]["timeout"] == 0.01


def test_local_plugin_install_caches_repo_and_preserves_lock_metadata(tmp_path):
    service = PluginService([], tmp_path / "storage", network_enabled=False)

    result = service.install(str(FIXTURE))
    state = PluginService([], tmp_path / "storage", network_enabled=False).discover()

    assert result.status == "installed"
    assert result.plugin_name == "superpowers"
    assert (tmp_path / "storage" / "plugins" / "superpowers" / "lock.json").exists()
    assert any(plugin["name"] == "superpowers" for plugin in state["plugins"])


def test_plugins_command_shows_superpowers_status(tmp_path):
    result = _runtime(tmp_path, [FIXTURE]).invoke("/plugins", input_kind="headless", project_root=tmp_path)

    assert "superpowers" in result["final_response"]
    assert "enabled" in result["final_response"]
    assert "skills: 4" in result["final_response"]
