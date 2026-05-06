"""Runtime tests for typed Pydantic skill argument validation and formatting."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import ToolMessage

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.graph.nodes.tool_router import tool_router_node
from langgraph_agent_blueprint.graph.state import create_initial_state
from langgraph_agent_blueprint.skills.args import GenericSkillArgs, RememberSkillArgs, VerifySkillArgs


def _runtime(tmp_path: Path) -> AssistantGraphRuntime:
    config = AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake")
    return AssistantGraphRuntime(build_dependencies(config))


def test_builtin_skill_registry_assigns_typed_arg_schemas(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))

    assert deps.skill_registry.get("remember").args_schema is RememberSkillArgs
    assert deps.skill_registry.get("verify").args_schema is VerifySkillArgs


def test_remember_accepts_string_and_defaults_to_session_scope(tmp_path):
    runtime = _runtime(tmp_path)

    runtime.invoke("/skill remember remember this", input_kind="headless", project_root=tmp_path, session_id="remember-session")
    result = runtime.invoke("/memory", input_kind="headless", project_root=tmp_path, session_id="remember-session")

    assert "session:" in result["final_response"]
    assert "remember this" in result["final_response"]


def test_remember_accepts_dict_args_from_skill_tool(tmp_path):
    runtime = _runtime(tmp_path)

    runtime.invoke(
        'tool:skill {"skill":"remember","args":{"text":"remember dict","scope":"project"}}',
        input_kind="headless",
        project_root=tmp_path,
    )
    result = runtime.invoke("/memory", input_kind="headless", project_root=tmp_path)

    assert "project:" in result["final_response"]
    assert "remember dict" in result["final_response"]


def test_remember_rejects_invalid_scope_with_tool_message(tmp_path):
    result = _runtime(tmp_path).invoke(
        'tool:skill {"skill":"remember","args":{"text":"bad","scope":"global"}}',
        input_kind="headless",
        project_root=tmp_path,
    )

    assert result["tool_results"][-1]["status"] == "error"
    assert result["tool_results"][-1]["metadata"]["error_type"] == "skill_args_validation"
    assert any(isinstance(message, ToolMessage) for message in result["messages"])
    assert "remember" not in result.get("memory", {})


def test_verify_accepts_task_and_commands(tmp_path):
    result = _runtime(tmp_path).invoke(
        'tool:skill {"skill":"verify","args":{"task":"run tests","commands":["pytest -q"]}}',
        input_kind="headless",
        project_root=tmp_path,
    )

    prompt = result["active_skill"]["result"]["prompt"]
    assert "task: run tests" in prompt
    assert "commands:" in prompt
    assert "- pytest -q" in prompt


def test_simplify_requires_content(tmp_path):
    result = _runtime(tmp_path).invoke('tool:skill {"skill":"simplify","args":{}}', input_kind="headless", project_root=tmp_path)

    assert result["tool_results"][-1]["status"] == "error"
    assert "content" in result["tool_results"][-1]["content"]


def test_skillify_supports_workflow_and_target_name(tmp_path):
    result = _runtime(tmp_path).invoke(
        'tool:skill {"skill":"skillify","args":{"workflow":"review changes","target_name":"reviewer"}}',
        input_kind="headless",
        project_root=tmp_path,
    )

    prompt = result["active_skill"]["result"]["prompt"]
    assert "workflow: review changes" in prompt
    assert "target_name: reviewer" in prompt


def test_file_based_unknown_skill_uses_generic_args_schema(tmp_path):
    skill_dir = tmp_path / "skills" / "custom"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: custom\ndescription: Custom skill\n---\nCustom args:\n{{args}}\n",
        encoding="utf-8",
    )
    deps = build_dependencies(
        AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", skills_paths=[tmp_path / "skills"])
    )

    assert deps.skill_registry.get("custom").args_schema is GenericSkillArgs

    result = AssistantGraphRuntime(deps).invoke("/skill custom hello generic", input_kind="headless", project_root=tmp_path)

    assert "hello generic" in result["active_skill"]["result"]["prompt"]


def test_allowed_tools_narrowing_still_works_after_typed_args(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    state = create_initial_state("call", project_root=tmp_path)
    skill_result = deps.skill_service.invoke("verify", {"task": "check", "commands": ["pytest -q"]}, state)
    state["metadata"] = {"allowed_tools_override": skill_result["allowed_tools"]}
    state["pending_tool_calls"] = [{"id": "call_1", "name": "write_file", "args": {"path": "x.txt", "content": "x"}}]

    update = tool_router_node(state, deps)

    assert update["tool_results"][0]["status"] == "rejected"
    assert update["tool_results"][0]["metadata"]["reason"] == "disallowed_by_skill"
