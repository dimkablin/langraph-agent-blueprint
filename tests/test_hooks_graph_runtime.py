"""Graph integration tests for hook lifecycle points."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.hooks import HookContribution, HookResult


def _runtime_with_hooks(tmp_path: Path, points: list[str]) -> AssistantGraphRuntime:
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    for point in points:
        hook_id = f"test.{point}"
        deps.hook_registry.register(HookContribution(id=hook_id, hook_point=point, trusted=True))  # type: ignore[arg-type]
        deps.hook_service.register_handler(
            hook_id,
            lambda invocation, point=point: HookResult(
                hook_id=invocation.hook.id,
                hook_point=invocation.context.hook_point,
                action="modify_metadata",
                data={"metadata": {"seen": point}},
            ),
        )
    return AssistantGraphRuntime(deps)


def _hook_event(result: dict, hook_point: str, event_type: str = "hook_finished") -> bool:
    return any(
        event["type"] == event_type and event["data"].get("hook_point") == hook_point
        for event in result.get("ui_events", [])
    )


def test_user_prompt_pre_model_and_post_model_hooks_fire_and_persist(tmp_path: Path) -> None:
    runtime = _runtime_with_hooks(tmp_path, ["user_prompt", "pre_model", "post_model"])

    result = runtime.invoke("hello", input_kind="headless", project_root=tmp_path, session_id="hook-session")
    loaded = runtime.dependencies.session_storage.load_session(tmp_path, "hook-session")

    assert _hook_event(result, "user_prompt")
    assert _hook_event(result, "pre_model")
    assert _hook_event(result, "post_model")
    assert any(event["type"] == "hook_started" for event in loaded["events"])


def test_pre_tool_and_post_tool_hooks_fire_on_read_file(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("hook runtime", encoding="utf-8")
    runtime = _runtime_with_hooks(tmp_path, ["pre_tool", "post_tool"])

    result = runtime.invoke('tool:read_file {"path":"README.md"}', input_kind="headless", project_root=tmp_path)

    assert _hook_event(result, "pre_tool")
    assert _hook_event(result, "post_tool")


def test_permission_request_and_resolved_hooks_fire(tmp_path: Path) -> None:
    runtime = _runtime_with_hooks(tmp_path, ["permission_request", "permission_resolved"])

    first = runtime.invoke("tool:write_file created.txt hello", input_kind="headless", project_root=tmp_path, thread_id="hook-permission")
    resumed = runtime.resume("hook-permission", {"approved": False, "reason": "test rejection"})

    assert "__interrupt__" in first
    assert _hook_event(first, "permission_request")
    assert _hook_event(resumed, "permission_resolved")


def test_pre_skill_and_post_skill_hooks_fire_on_explicit_skill(tmp_path: Path) -> None:
    runtime = _runtime_with_hooks(tmp_path, ["pre_skill", "post_skill"])

    result = runtime.invoke("/skill remember session: hooks matter", input_kind="headless", project_root=tmp_path)

    assert _hook_event(result, "pre_skill")
    assert _hook_event(result, "post_skill")


def test_hook_block_action_stops_model_response(tmp_path: Path) -> None:
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    deps.hook_registry.register(HookContribution(id="test.block", hook_point="pre_model", trusted=True))
    deps.hook_service.register_handler(
        "test.block",
        lambda invocation: HookResult(
            hook_id=invocation.hook.id,
            hook_point="pre_model",
            action="block",
            message="blocked by hook",
            severity="warning",
        ),
    )
    runtime = AssistantGraphRuntime(deps)

    result = runtime.invoke("hello", input_kind="headless", project_root=tmp_path)

    assert result["final_response"] == "blocked by hook"
    assert any(event["type"] == "hook_blocked" for event in result["ui_events"])
    assert not any(event["type"] == "model_message" for event in result["ui_events"])

