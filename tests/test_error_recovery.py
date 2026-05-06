"""Pytest coverage for error recovery behavior in the Python/LangGraph assistant."""

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.tools.base import BaseTool, ToolExecutionContext, ToolSafety
from pydantic import BaseModel


class FailingInput(BaseModel):
    """Input schema for a test tool that always raises."""

    value: str = "x"


class FailingOutput(BaseModel):
    """Output schema placeholder for the failing test tool."""

    ok: bool


class FailingTool(BaseTool[FailingInput, FailingOutput]):
    """Test-only tool used to verify graph error recovery behavior."""

    name = "fail"
    description = "Fails for tests"
    input_schema = FailingInput
    output_schema = FailingOutput
    safety = ToolSafety.READ_ONLY
    is_read_only = True
    requires_permission = False

    def run(self, data: FailingInput, context: ToolExecutionContext) -> FailingOutput:
        raise RuntimeError("boom")


def test_tool_exception_goes_to_error_recovery_without_crashing(tmp_path):
    deps = build_dependencies(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    deps.tool_registry.register(FailingTool())
    runtime = AssistantGraphRuntime(deps)

    result = runtime.invoke("tool:fail", input_kind="headless")

    assert result["errors"][0]["message"] == "boom"
    assert "boom" in result["final_response"]

