"""Contract tests for extensible agent activity payloads."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.models import AgentActivityEvent, AgentActivitySource, ToolActivitySpec
from langgraph_agent_blueprint.models.prompts import BASE_SYSTEM_PROMPT
from langgraph_agent_blueprint.services import AgentService
from langgraph_agent_blueprint.tools.agent_tools import AgentInput, AgentTool


def test_activity_event_type_is_open_namespaced_string() -> None:
    event = AgentActivityEvent(
        id="activity_custom",
        type="vendor.custom_tool.started",
        source=AgentActivitySource(kind="tool", name="custom_tool"),
        category="tool",
        status="running",
        title="Custom tool started",
    )

    assert event.type == "vendor.custom_tool.started"
    assert AgentActivityEvent.model_fields["type"].annotation is str


def test_no_central_agent_activity_event_type_is_exported() -> None:
    import langgraph_agent_blueprint.models as models

    assert not hasattr(models, "AgentActivityEventType")


def test_tool_activity_spec_is_part_of_tool_metadata_contract() -> None:
    spec = ToolActivitySpec(
        display_name="Custom Probe",
        started_type="custom.probe.started",
        completed_type="custom.probe.completed",
        failed_type="custom.probe.failed",
        blocked_type="custom.probe.blocked",
    )

    assert spec.category == "tool"
    assert spec.started_type == "custom.probe.started"
    assert spec.completed_type == "custom.probe.completed"


def test_agent_tool_metadata_tells_models_to_start_subagents_with_tool_calls() -> None:
    metadata = AgentTool(AgentService()).metadata()
    description = metadata["description"].lower()
    input_schema = metadata["input_schema"]

    assert "create" in description
    assert "delegate" in description
    assert "subagent" in description
    assert "does not start" in description
    assert input_schema["properties"]["prompt"]["description"]
    assert "frontend" in input_schema["properties"]["name"]["description"]
    assert "backend" in input_schema["properties"]["name"]["description"]
    assert "allowed_tools" in input_schema["properties"]
    assert "allowedTools" in input_schema["properties"]["allowed_tools"]["description"]


def test_agent_input_rejects_camel_case_allowed_tools_payload() -> None:
    with pytest.raises(ValidationError):
        AgentInput.model_validate({"prompt": "Build frontend", "allowedTools": ["write_file"]})


def test_system_prompt_requires_agent_tool_calls_for_subagent_requests() -> None:
    prompt = BASE_SYSTEM_PROMPT.lower()

    assert "сабагент" in prompt
    assert "саб-агент" in prompt
    assert "sub-agent" in prompt
    assert "frontend/backend" in prompt
    assert "allowed_tools" in prompt
    assert "allowedtools" in prompt
    assert "call the `agent` tool once" in prompt
    assert "final answer is allowed only after required tool calls" in prompt


def test_tool_executor_does_not_map_tool_names_to_activity_types() -> None:
    root = Path(__file__).resolve().parents[1]
    inspected = [
        root / "src" / "langgraph_agent_blueprint" / "services" / "tool_execution_service.py",
        root / "src" / "langgraph_agent_blueprint" / "graph" / "nodes" / "tool_executor.py",
    ]
    concrete_tool_names = {"bash", "powershell", "read_file", "write_file", "edit_file", "glob", "grep"}

    for path in inspected:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        comparisons = _string_equality_comparisons(tree)
        assert not comparisons & concrete_tool_names, f"{path} hardcodes activity mapping for {comparisons & concrete_tool_names}"


def _string_equality_comparisons(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(operator, ast.Eq) for operator in node.ops):
            continue
        if not _looks_like_tool_name_reference(node.left):
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                values.add(comparator.value)
    return values


def _looks_like_tool_name_reference(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in {"name", "tool_name"}
    if isinstance(node, ast.Attribute):
        return node.attr == "name" and _name_root(node.value) in {"call", "tool", "result"}
    if isinstance(node, ast.Call):
        return _call_reads_tool_name(node)
    return False


def _name_root(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _name_root(node.value)
    return None


def _call_reads_tool_name(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
        return False
    if not node.args:
        return False
    key = node.args[0]
    return isinstance(key, ast.Constant) and key.value in {"name", "tool_name"}
