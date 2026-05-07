"""Regression tests for controlled hook result application."""

from __future__ import annotations

from langgraph_agent_blueprint.hooks.applier import apply_hook_results
from langgraph_agent_blueprint.models.hooks import HookResult


def test_add_system_context_does_not_mutate_input_metadata_lists() -> None:
    metadata_fragments = ["existing"]
    hook_fragments = [{"hook_id": "old", "content": "existing"}]
    state = {
        "metadata": {"hook_system_context_fragments": metadata_fragments},
        "hooks_state": {"system_context_fragments": hook_fragments},
        "context_status": {"system_context": "existing"},
    }
    result = HookResult(
        hook_id="plugin.add",
        hook_point="pre_model",
        action="add_system_context",
        data={"plugin_name": "plugin", "content": "new context"},
    )

    update = apply_hook_results(state, [result])

    assert state["metadata"]["hook_system_context_fragments"] == ["existing"]
    assert state["hooks_state"]["system_context_fragments"] == [{"hook_id": "old", "content": "existing"}]
    assert state["metadata"]["hook_system_context_fragments"] is metadata_fragments
    assert state["hooks_state"]["system_context_fragments"] is hook_fragments
    assert update["metadata"]["hook_system_context_fragments"] == ["existing", "[plugin hook: plugin.add] new context"]
    assert update["hooks_state"]["system_context_fragments"][-1]["hook_id"] == "plugin.add"


def test_modify_metadata_does_not_mutate_existing_hook_metadata() -> None:
    hook_metadata = {"old": {"value": 1}}
    state = {"metadata": {"hook_metadata": hook_metadata}}
    result = HookResult(
        hook_id="new",
        hook_point="pre_model",
        action="modify_metadata",
        data={"metadata": {"value": 2}},
    )

    update = apply_hook_results(state, [result])

    assert state["metadata"]["hook_metadata"] == {"old": {"value": 1}}
    assert update["metadata"]["hook_metadata"] == {"old": {"value": 1}, "new": {"value": 2}}
