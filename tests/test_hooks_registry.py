"""Tests for HookRegistry behavior."""

from __future__ import annotations

import pytest

from langgraph_agent_blueprint.hooks.registry import HookRegistry
from langgraph_agent_blueprint.models.hooks import HookContribution


def test_registry_registers_and_lists_by_hook_point_with_priority_sort() -> None:
    registry = HookRegistry()
    low = HookContribution(id="test.low", hook_point="pre_model", priority=200)
    high = HookContribution(id="test.high", hook_point="pre_model", priority=10)

    registry.register(low)
    registry.register(high)

    assert [hook.id for hook in registry.get_for_point("pre_model")] == ["test.high", "test.low"]
    assert [hook.id for hook in registry.list_hooks()] == ["test.high", "test.low"]


def test_registry_rejects_duplicate_ids_without_replace() -> None:
    registry = HookRegistry()
    contribution = HookContribution(id="test.duplicate", hook_point="post_model")

    registry.register(contribution)

    with pytest.raises(ValueError, match="Duplicate hook id"):
        registry.register(contribution)


def test_registry_can_disable_hook() -> None:
    registry = HookRegistry()
    registry.register(HookContribution(id="test.enabled", hook_point="pre_tool"))

    registry.set_enabled("test.enabled", False)

    assert registry.get_for_point("pre_tool") == []
    assert registry.get("test.enabled").enabled is False


def test_registry_groups_hooks_by_plugin_name() -> None:
    registry = HookRegistry()
    registry.register(HookContribution(id="plugin.context", plugin_name="demo", hook_point="pre_context_build"))

    assert registry.group_by_plugin()["demo"][0].id == "plugin.context"

