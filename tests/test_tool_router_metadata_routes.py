"""Regression tests for metadata-driven tool routing."""

from __future__ import annotations

from pydantic import BaseModel

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.nodes.tool_router import tool_router_node
from langgraph_agent_blueprint.graph.state import create_initial_state
from langgraph_agent_blueprint.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.tools.base import BaseTool, ToolExecutionContext, ToolOutput


class EmptyInput(BaseModel):
    """Minimal input schema used by metadata-routing test tools."""


class NoopOutput(ToolOutput):
    """Minimal output schema used by metadata-routing test tools."""


class RouteTestTool(BaseTool[EmptyInput, NoopOutput]):
    """Custom tool whose route is intentionally independent from its name."""

    description = "Route test tool."
    input_schema = EmptyInput
    output_schema = NoopOutput
    permission = ToolPermissionMetadata(action="read", risk="low", is_read_only=True, allowed_in_plan_mode=True)

    def __init__(self, name: str, route: str, kind: str = "custom") -> None:
        self.name = name
        self.runtime = ToolRuntimeMetadata(kind=kind, route=route)

    def run(self, data: EmptyInput, context: ToolExecutionContext) -> NoopOutput:
        return NoopOutput(content="ok")


def _deps(tmp_path):
    return build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))


def _route_for(tmp_path, tool: RouteTestTool, args: dict | None = None) -> dict:
    deps = _deps(tmp_path)
    deps.tool_registry.register(tool)
    state = create_initial_state("route", project_root=tmp_path)
    state["pending_tool_calls"] = [{"id": "route_1", "name": tool.name, "args": args or {}}]
    return tool_router_node(state, deps)


def test_skill_route_comes_from_runtime_metadata_not_tool_name(tmp_path):
    update = _route_for(
        tmp_path,
        RouteTestTool("custom_skill_runner", "skill_graph", "skill"),
        {"skill": "verify", "args": "run checks"},
    )

    assert update["metadata"]["tool_route"] == "skill_tool"
    assert update["active_skill"]["name"] == "verify"


def test_agent_route_comes_from_runtime_metadata_not_tool_name(tmp_path):
    update = _route_for(tmp_path, RouteTestTool("delegate_elsewhere", "agent_graph", "agent"))

    assert update["metadata"]["tool_route"] == "agent_tool"


def test_mcp_route_comes_from_runtime_metadata_without_mcp_prefix(tmp_path):
    update = _route_for(tmp_path, RouteTestTool("external_echo", "mcp_graph", "mcp"))

    assert update["metadata"]["tool_route"] == "mcp_tool"


def test_tool_named_skill_can_execute_when_metadata_route_is_execute(tmp_path):
    update = _route_for(tmp_path, RouteTestTool("skill", "execute", "custom"))

    assert update["metadata"]["tool_route"] == "execute"
    assert "active_skill" not in update
