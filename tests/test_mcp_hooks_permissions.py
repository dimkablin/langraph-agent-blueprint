"""MCP regressions for hooks and permission preservation."""

from __future__ import annotations

import sys
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.hooks import HookContribution, HookResult


def _runtime_with_hooks(tmp_path: Path, points: list[str]) -> AssistantGraphRuntime:
    server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
    deps = build_dependencies(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            llm_provider="fake",
            mcp_config={
                "servers": {
                    "fake": {
                        "enabled": True,
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [str(server)],
                    }
                }
            },
        )
    )
    for point in points:
        hook_id = f"test.mcp.{point}"
        deps.hook_registry.register(HookContribution(id=hook_id, hook_point=point, trusted=True))  # type: ignore[arg-type]
        deps.hook_service.register_handler(
            hook_id,
            lambda invocation, point=point: HookResult(
                hook_id=invocation.hook.id,
                hook_point=invocation.context.hook_point,
                action="modify_metadata",
                data={"metadata": {"last_mcp_hook": point}},
            ),
        )
    return AssistantGraphRuntime(deps)


def _hook_event(result: dict, hook_point: str, event_type: str = "hook_finished") -> bool:
    return any(event["type"] == event_type and event["data"].get("hook_point") == hook_point for event in result.get("ui_events", []))


def test_pre_tool_and_post_tool_hooks_fire_for_mcp_tool_calls(tmp_path: Path) -> None:
    runtime = _runtime_with_hooks(tmp_path, ["pre_tool", "post_tool"])
    try:
        first = runtime.invoke(
            'tool:mcp.fake.echo {"text":"hooked"}',
            input_kind="headless",
            project_root=tmp_path,
            thread_id="mcp-hook",
        )
        result = runtime.resume("mcp-hook", {"approved": True})
    finally:
        runtime.dependencies.mcp_service.close()

    assert "__interrupt__" in first
    assert _hook_event(first, "pre_tool")
    assert _hook_event(result, "post_tool")


def test_mcp_tools_cannot_bypass_permission_service(tmp_path: Path) -> None:
    runtime = _runtime_with_hooks(tmp_path, [])
    try:
        first = runtime.invoke(
            'tool:mcp.fake.make_note {"note":"requires approval"}',
            input_kind="headless",
            project_root=tmp_path,
            thread_id="mcp-permission",
        )
    finally:
        runtime.dependencies.mcp_service.close()

    assert "__interrupt__" in first
    assert first["pending_confirmation"]["tool_name"] == "mcp.fake.make_note"
    assert first["pending_confirmation"]["action"] == "mcp"
