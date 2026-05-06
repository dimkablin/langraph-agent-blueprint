"""Integration tests that ensure boundary DTOs are used by the graph runtime."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, ToolMessage

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.events import RuntimeEvent
from langgraph_agent_blueprint.models.llm import ModelRequest
from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.tools import ToolCall, ToolResult
from langgraph_agent_blueprint.services.model_provider import ModelProviderService


def test_legacy_event_helper_returns_runtime_event_payload():
    payload = event("tool_call_started", id="call_1", name="read_file")

    restored = RuntimeEvent.model_validate(payload)

    assert restored.session_id == "unknown"
    assert restored.data["id"] == "call_1"
    assert restored.type == "tool_call_started"


def test_fake_provider_tool_calls_are_typed_boundary_payloads():
    provider = ModelProviderService(AppConfig(llm_provider="fake"))

    response = provider.generate(ModelRequest(messages=[HumanMessage(content='tool:read_file {"path":"README.md"}')]))

    call = ToolCall.model_validate(response.tool_calls[0])
    assert call.name == "read_file"
    assert call.provider == "fake"
    assert call.args == {"path": "README.md"}


def test_graph_tool_execution_results_validate_as_typed_payloads(tmp_path):
    (tmp_path / "README.md").write_text("boundary wiring", encoding="utf-8")
    runtime = AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )

    result = runtime.invoke('tool:read_file {"path":"README.md"}', input_kind="headless", project_root=tmp_path)

    assert ToolResult.model_validate(result["tool_results"][-1]).status == "ok"
    assert any(isinstance(message, ToolMessage) for message in result["messages"])
    assert all(RuntimeEvent.model_validate(item) for item in result["ui_events"])
