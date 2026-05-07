"""AgentTool schema and metadata tests for real subagent runtime."""

from __future__ import annotations

from langgraph_agent_blueprint.tools.agent_tools import AgentInput, AgentTool
from langgraph_agent_blueprint.services.agent_service import AgentService


def test_agent_tool_input_maps_to_subagent_request_fields() -> None:
    data = AgentInput.model_validate(
        {
            "prompt": "Search the repo and summarize permissions.",
            "name": "repo-investigator",
            "purpose": "Investigate permission runtime",
            "allowed_tools": ["read_file", "grep", "glob"],
            "max_turns": 6,
            "timeout_seconds": 45,
        }
    )

    request = data.to_request()

    assert request.prompt == data.prompt
    assert request.name == "repo-investigator"
    assert request.allowed_tools == ["read_file", "grep", "glob"]
    assert request.max_turns == 6


def test_agent_tool_routes_to_agent_graph_and_keeps_permission_metadata() -> None:
    tool = AgentTool(AgentService())

    assert tool.runtime.route == "agent_graph"
    assert tool.permission.action == "agent"
    assert tool.permission.requires_permission is False

