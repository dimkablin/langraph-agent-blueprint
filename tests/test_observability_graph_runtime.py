"""Graph runtime integration tests for observability callbacks and event tracing."""

from __future__ import annotations

import sys
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.hooks import HookContribution, HookResult
from langgraph_agent_blueprint.models.observability import LangfuseConfig
from langgraph_agent_blueprint.services.observability_service import ObservabilityService

from tests.test_observability_service import RecordingLangfuseFactory


def test_graph_with_observability_disabled_still_runs(tmp_path: Path) -> None:
    deps = build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    runtime = AssistantGraphRuntime(deps)

    result = runtime.invoke("hello", input_kind="headless", project_root=tmp_path)

    assert result["final_response"] == "Fake response: hello"
    assert deps.observability_service.status()["mode"] == "disabled"


def _runtime(tmp_path: Path, *, mcp: bool = False) -> tuple[AssistantGraphRuntime, RecordingLangfuseFactory]:
    factory = RecordingLangfuseFactory()
    mcp_config = {}
    if mcp:
        server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
        mcp_config = {
            "servers": {
                "fake": {
                    "enabled": True,
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [str(server)],
                    "timeout_seconds": 5,
                }
            }
        }
    deps = build_dependencies(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            llm_provider="fake",
            mcp_config=mcp_config,
            langfuse=LangfuseConfig(
                enabled=True,
                public_key="pk",
                secret_key="sk",
                base_url="https://langfuse.example",
                environment="ci",
            ),
        )
    )
    deps.observability_service = ObservabilityService(deps.config.langfuse, factory=factory)
    deps.hook_registry.register(HookContribution(id="obs.test.pre_model", hook_point="pre_model", trusted=True))
    deps.hook_service.register_handler(
        "obs.test.pre_model",
        lambda invocation: HookResult(hook_id=invocation.hook.id, hook_point=invocation.context.hook_point),
    )
    return AssistantGraphRuntime(deps), factory


def test_graph_invoke_attaches_callbacks_and_records_final_response(tmp_path: Path) -> None:
    runtime, factory = _runtime(tmp_path)

    result = runtime.invoke("hello", input_kind="headless", project_root=tmp_path, thread_id="obs-thread")

    assert result["final_response"] == "Fake response: hello"
    assert factory.callbacks_created == 1
    assert len(factory.client.top_level_traces) == 1
    assert factory.client.unscoped_events == []
    assert any(event["name"] == "runtime.final_response" for event in factory.client.child_observations)
    assert factory.client.top_level_traces[0]["trace_id"] == factory.client.child_observations[0]["trace_id"]
    assert factory.client.top_level_traces[0]["session_id"] == result["session_id"]


def test_graph_callback_nested_under_turn_trace(tmp_path: Path) -> None:
    runtime, factory = _runtime(tmp_path)

    runtime.invoke("hello", input_kind="headless", project_root=tmp_path, thread_id="obs-callback")

    assert factory.client.top_level_traces
    assert factory.handlers[0].active_trace_id == factory.client.top_level_traces[0]["trace_id"]


def test_graph_records_tool_skill_permission_hook_and_mcp_events(tmp_path: Path) -> None:
    runtime, factory = _runtime(tmp_path, mcp=True)
    try:
        read_result = runtime.invoke('tool:read_file {"path":"README.md"}', input_kind="headless", project_root=tmp_path)
        skill_result = runtime.invoke("/skill remember session: observability", input_kind="headless", project_root=tmp_path)
        first = runtime.invoke(
            'tool:mcp.fake.echo {"text":"hello"}',
            input_kind="headless",
            project_root=tmp_path,
            thread_id="obs-mcp",
        )
        mcp_result = runtime.resume("obs-mcp", {"approved": True})
    finally:
        runtime.dependencies.mcp_service.close()

    names = [event["name"] for event in factory.client.child_observations]
    assert read_result["final_response"]
    assert skill_result["final_response"]
    assert "__interrupt__" in first
    assert mcp_result["tool_results"][-1]["status"] == "ok"
    assert "runtime.tool_call_started" in names
    assert "runtime.skill_started" in names
    assert "runtime.permission_required" in names
    assert "runtime.permission_resolved" in names
    assert "runtime.mcp_tool_call_finished" in names
    assert any("runtime.hook_" in str(update) for update in factory.client.metadata_updates)
    assert factory.client.unscoped_events == []


def test_stream_trace_context_lives_until_generator_exhausted(tmp_path: Path) -> None:
    runtime, factory = _runtime(tmp_path)

    events = list(runtime.stream("hello", input_kind="headless", project_root=tmp_path, thread_id="obs-stream"))

    assert events
    assert len(factory.client.top_level_traces) == 1
    assert factory.client.unscoped_events == []
    assert any(event["name"] == "runtime.final_response" for event in factory.client.child_observations)
    assert factory.client.flushed is True


def test_two_headless_invocations_can_have_separate_sessions(tmp_path: Path) -> None:
    runtime, factory = _runtime(tmp_path)

    first = runtime.invoke("hello", input_kind="headless", project_root=tmp_path)
    second = runtime.invoke("again", input_kind="headless", project_root=tmp_path)

    assert first["session_id"] != second["session_id"]
    assert len(factory.client.top_level_traces) == 2
    assert {trace["session_id"] for trace in factory.client.top_level_traces} == {first["session_id"], second["session_id"]}
