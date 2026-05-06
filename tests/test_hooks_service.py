"""Tests for HookService and controlled HookResult application."""

from __future__ import annotations

from langgraph_agent_blueprint.hooks.applier import apply_hook_results
from langgraph_agent_blueprint.hooks.registry import HookRegistry
from langgraph_agent_blueprint.models.hooks import HookContext, HookContribution, HookResult
from langgraph_agent_blueprint.services.hook_service import HookService


def test_builtin_hook_returns_continue_and_events() -> None:
    registry = HookRegistry()
    contribution = HookContribution(id="test.continue", hook_point="pre_model", trusted=True)
    registry.register(contribution)
    service = HookService(registry)
    service.register_handler("test.continue", lambda invocation: HookResult(hook_id=invocation.hook.id, hook_point="pre_model"))

    summary = service.run(HookContext(session_id="session-1", hook_point="pre_model"))

    assert [result.action for result in summary.results] == ["continue"]
    assert [event["type"] for event in summary.events] == ["hook_started", "hook_finished"]


def test_builtin_hook_can_add_system_context_through_result() -> None:
    registry = HookRegistry()
    contribution = HookContribution(id="test.context", hook_point="pre_model", trusted=True)
    registry.register(contribution)
    service = HookService(registry)
    service.register_handler(
        "test.context",
        lambda invocation: HookResult(
            hook_id=invocation.hook.id,
            hook_point="pre_model",
            action="add_system_context",
            data={"content": "runtime context"},
        ),
    )

    summary = service.run(HookContext(session_id="session-1", hook_point="pre_model"))
    update = apply_hook_results({"metadata": {}, "context_status": {"system_context": "base"}}, summary.results)

    assert "runtime context" in update["metadata"]["hook_system_context_fragments"][0]
    assert "runtime context" in update["context_status"]["system_context"]


def test_hook_error_returns_error_result_and_event() -> None:
    registry = HookRegistry()
    contribution = HookContribution(id="test.error", hook_point="post_model", trusted=True)
    registry.register(contribution)
    service = HookService(registry)

    def fail(_invocation):
        raise RuntimeError("boom")

    service.register_handler("test.error", fail)

    summary = service.run(HookContext(session_id="session-1", hook_point="post_model"))

    assert summary.results[0].action == "error"
    assert summary.events[-1]["type"] == "hook_error"
    assert "boom" in summary.events[-1]["data"]["error"]


def test_disabled_hook_is_ignored() -> None:
    registry = HookRegistry()
    registry.register(HookContribution(id="test.disabled", hook_point="pre_tool", enabled=False))
    service = HookService(registry)

    summary = service.run(HookContext(session_id="session-1", hook_point="pre_tool"))

    assert summary.results == []
    assert summary.events == []


def test_applier_does_not_allow_forbidden_state_mutation() -> None:
    result = HookResult(
        hook_id="test.security",
        hook_point="pre_model",
        action="modify_metadata",
        data={"metadata": {"safe": True}, "messages": ["forbidden"]},
    )

    update = apply_hook_results({"metadata": {}, "messages": ["original"]}, [result])

    assert "messages" not in update
    assert update["metadata"]["hook_metadata"]["test.security"]["safe"] is True

