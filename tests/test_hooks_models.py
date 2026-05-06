"""Tests for typed hook boundary models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.models.hooks import (
    HookContext,
    HookContribution,
    HookInvocation,
    HookResult,
    HookRuntimeMetadata,
)


def test_hook_contribution_validates_known_hook_point() -> None:
    contribution = HookContribution(id="test.pre_model", hook_point="pre_model", description="test")

    assert contribution.id == "test.pre_model"
    assert contribution.hook_point == "pre_model"
    assert contribution.priority == 100
    assert contribution.enabled is True


def test_hook_contribution_rejects_invalid_hook_point() -> None:
    with pytest.raises(ValidationError):
        HookContribution(id="test.invalid", hook_point="before_everything")  # type: ignore[arg-type]


def test_hook_invocation_and_result_are_typed() -> None:
    contribution = HookContribution(id="test.user_prompt", hook_point="user_prompt")
    context = HookContext(session_id="session-1", thread_id="thread-1", hook_point="user_prompt", input_text="hello")
    invocation = HookInvocation(hook=contribution, context=context)
    result = HookResult(
        hook_id=contribution.id,
        hook_point="user_prompt",
        action="add_system_context",
        data={"content": "context from hook"},
    )

    assert invocation.hook.id == "test.user_prompt"
    assert invocation.context.input_text == "hello"
    assert result.action == "add_system_context"


def test_hook_runtime_metadata_is_data_only() -> None:
    metadata = HookRuntimeMetadata(action="add_system_context", content="Use concise output.")

    assert metadata.kind == "declarative"
    assert metadata.action == "add_system_context"
    assert metadata.content == "Use concise output."

