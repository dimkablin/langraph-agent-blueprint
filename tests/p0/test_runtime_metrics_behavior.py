"""Behavioral coverage for runtime latency instrumentation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.models import AgentRunInput

from .helpers import ai_final, ai_tool_call, expect_tool_result, expect_user_message, scripted_shell, shell_ok


def test_runtime_metrics_event_emits_safe_turn_node_model_and_persistence_metrics(
    runtime_factory: Any,
    scripted_chat_model: Any,
    approving_permissions: Any,
    temp_project: Path,
) -> None:
    model = scripted_chat_model(
        steps=[
            expect_user_message("Read README."),
            ai_final("README inspected."),
        ]
    )
    runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)

    result = runtime.run(AgentRunInput(message="Read README.", project_root=str(temp_project)))

    metrics_event = _single_metrics_event(result.events)
    metrics = metrics_event["data"]["metrics"]
    assert metrics["total_duration_ms"] >= 0
    assert metrics["event_count"] == len(result.events)
    assert metrics["model_provider_duration_ms"] >= 0
    assert metrics["persistence_duration_ms"] >= 0
    assert metrics["tool_schema_payload_chars"] > 0
    assert metrics["tool_schema_token_estimate"] > 0
    assert metrics["node_durations_ms"]["model_call"] >= 0
    assert metrics["node_durations_ms"]["persist_session"] >= 0
    assert "tool_durations_ms" not in metrics or metrics["tool_durations_ms"] == []

    rendered = json.dumps(metrics_event, sort_keys=True)
    assert "Read README" not in rendered
    assert str(temp_project) not in rendered
    assert "api_key" not in rendered.lower()
    model.assert_no_unused_steps()


def test_context_builder_reuses_cached_session_memory_and_records_metrics(
    runtime_factory: Any,
    scripted_chat_model: Any,
    approving_permissions: Any,
    temp_project: Path,
) -> None:
    session_id = "t95363b6b-memory-cache"
    model = scripted_chat_model(
        steps=[
            expect_user_message("Prime memory."),
            ai_final("Primed."),
            expect_user_message("Reuse memory."),
            ai_final("Reused."),
        ]
    )
    runtime = runtime_factory(project_root=temp_project, chat_model=model, permissions=approving_permissions)
    runtime.dependencies.memory_service.remember("session", "Session-scoped note for cache behavior.", session_id=session_id)

    call_count = {"count": 0}
    original_load_memory = runtime.dependencies.memory_service.load_memory

    def tracking_load_memory(project_root: str | None, session_id_param: str | None = None) -> dict[str, str]:
        call_count["count"] += 1
        return original_load_memory(project_root, session_id_param)

    runtime.dependencies.memory_service.load_memory = tracking_load_memory

    runtime.run(AgentRunInput(message="Prime memory.", project_root=str(temp_project), session_id=session_id))
    assert call_count["count"] == 1

    call_count["count"] = 0
    result = runtime.run(AgentRunInput(message="Reuse memory.", project_root=str(temp_project), session_id=session_id))
    assert call_count["count"] == 0

    metrics = _single_metrics_event(result.events)["data"]["metrics"]
    assert metrics["context_builder_memory_cache_hit"] is True
    assert metrics["memory_scope_count"] == 3
    assert metrics["memory_context_chars"] >= len("session memory:\nSession-scoped note for cache behavior.")
    model.assert_no_unused_steps()


def test_runtime_metrics_include_tool_duration_without_tool_arguments(
    runtime_factory: Any,
    scripted_chat_model: Any,
    approving_permissions: Any,
    temp_project: Path,
) -> None:
    model = scripted_chat_model(
        steps=[
            expect_user_message("Run verification."),
            ai_tool_call("bash", {"command": "python -m pytest -q"}, call_id="call_verify"),
            expect_tool_result("call_verify", contains="1 passed"),
            ai_final("Verification complete."),
        ]
    )
    runtime = runtime_factory(
        project_root=temp_project,
        chat_model=model,
        permissions=approving_permissions,
        shell_executor=scripted_shell({"python -m pytest -q": [shell_ok("1 passed")]}),
    )

    result = runtime.run(AgentRunInput(message="Run verification.", project_root=str(temp_project)))

    metrics = _single_metrics_event(result.events)["data"]["metrics"]
    tool_durations = metrics["tool_durations_ms"]
    assert tool_durations == [{"id": "call_verify", "name": "bash", "duration_ms": tool_durations[0]["duration_ms"]}]
    assert tool_durations[0]["duration_ms"] >= 0
    finished = [item for item in result.events if item["type"] == "tool_call_finished" and item["data"].get("id") == "call_verify"]
    assert finished and finished[0]["data"]["duration_ms"] >= 0

    rendered = json.dumps(_single_metrics_event(result.events), sort_keys=True)
    assert "python -m pytest -q" not in rendered
    model.assert_no_unused_steps()


def _single_metrics_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [item for item in events if item["type"] == "runtime_metrics"]
    assert len(matches) == 1
    return matches[0]
