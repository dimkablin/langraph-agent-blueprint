"""Pydantic tests for Phase 8 plugin SDK contribution models."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from langgraph_agent_blueprint.models.plugins import (
    PluginCommandContribution,
    PluginContextProviderContribution,
    PluginMCPContribution,
    PluginToolContribution,
    PluginTrustPolicy,
)


def test_plugin_sdk_models_validate_manifest_contributions() -> None:
    command = PluginCommandContribution(plugin_name="example_plugin", name="hello", command_type="static_response", response="hi")
    tool = PluginToolContribution(plugin_name="example_plugin", name="static", kind="static_text", response="tool hi")
    mcp = PluginMCPContribution(plugin_name="example_plugin", server_name="fake", registry_name="example_plugin.fake", config={"transport": "stdio"})
    context = PluginContextProviderContribution(plugin_name="example_plugin", name="reference", kind="static", content="docs")
    trust = PluginTrustPolicy()

    assert command.registry_name == "hello"
    assert tool.registry_name == "plugin.example_plugin.static"
    assert mcp.registry_name == "example_plugin.fake"
    assert context.trust == "plugin_provided"
    assert trust.level == "untrusted"


def test_plugin_sdk_rejects_empty_names() -> None:
    with pytest.raises(ValidationError):
        PluginCommandContribution(plugin_name="example", name="", command_type="static_response")

