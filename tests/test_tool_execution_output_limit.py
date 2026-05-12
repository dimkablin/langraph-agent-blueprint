"""Regression tests for model-facing tool result output limits."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.models import ToolResult, tool_result_to_tool_message
from langgraph_agent_blueprint.services.tool_execution_service import ToolExecutionService
from langgraph_agent_blueprint.tools import BaseTool, ToolExecutionContext, ToolOutput, ToolRegistry


class LongOutputInput(BaseModel):
    content: str


class LongOutputTool(BaseTool[LongOutputInput, ToolOutput]):
    name = "long_output"
    description = "Return exactly the requested content."
    input_schema = LongOutputInput
    output_schema = ToolOutput

    def run(self, data: LongOutputInput, context: ToolExecutionContext) -> ToolOutput:
        return ToolOutput(content=data.content, metadata={"fixture": "long_output"})


class FailingLongOutputTool(BaseTool[LongOutputInput, ToolOutput]):
    name = "failing_long_output"
    description = "Raise the requested content as an error."
    input_schema = LongOutputInput
    output_schema = ToolOutput

    def run(self, data: LongOutputInput, context: ToolExecutionContext) -> ToolOutput:
        raise RuntimeError(data.content)


def test_tool_output_limit_can_be_configured_from_environment(tmp_path: Path) -> None:
    config = AppConfig.from_env(
        project_root=tmp_path,
        user_config_path=tmp_path / "missing-user.toml",
        project_config_path=tmp_path / "missing-project.toml",
        environ={"LG_AGENT_TOOL_OUTPUT_LIMIT": "512"},
    )

    assert config.tool_output_limit == 512


def test_tool_execution_truncates_model_facing_tool_result_content(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register(LongOutputTool())
    service = ToolExecutionService(registry, output_limit=128)
    raw_content = "x" * 1000

    record = service.execute(
        {"id": "call_long", "name": "long_output", "args": {"content": raw_content}},
        _state(tmp_path),
    )

    result = ToolResult.model_validate(record)
    tool_message_payload = json.loads(tool_result_to_tool_message(result).content)

    assert len(result.content) <= 128
    assert result.content == tool_message_payload["content"]
    assert result.content == result.output["content"]
    assert result.content != raw_content
    assert result.metadata["content_truncated"] is True
    assert result.metadata["original_content_chars"] == len(raw_content)
    assert result.metadata["content_limit_chars"] == 128


def test_tool_execution_truncates_model_facing_error_result_content(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register(FailingLongOutputTool())
    service = ToolExecutionService(registry, output_limit=128)
    raw_content = "x" * 1000

    record = service.execute(
        {"id": "call_error", "name": "failing_long_output", "args": {"content": raw_content}},
        _state(tmp_path),
    )

    result = ToolResult.model_validate(record)
    tool_message_payload = json.loads(tool_result_to_tool_message(result).content)

    assert result.status == "error"
    assert len(result.content) <= 128
    assert result.content == tool_message_payload["content"]
    assert result.content != raw_content
    assert result.metadata["content_truncated"] is True
    assert result.metadata["original_content_chars"] == len(raw_content)
    assert result.metadata["content_limit_chars"] == 128


def _state(project_root: Path) -> dict[str, object]:
    return {
        "project_root": str(project_root),
        "cwd": str(project_root),
        "session_id": "session_test",
        "thread_id": "thread_test",
        "metadata": {},
    }
