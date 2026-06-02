"""Unit coverage for runtime permission mode overrides."""

from __future__ import annotations

from dataclasses import dataclass

from langgraph_agent_blueprint.models import ToolPermissionMetadata
from langgraph_agent_blueprint.services.permission_service import PermissionService


@dataclass
class ToolStub:
    permission: ToolPermissionMetadata
    name: str = "write_file"


def test_default_permission_mode_asks_for_mutating_tool_permission() -> None:
    tool = ToolStub(ToolPermissionMetadata(action="write", risk="medium", requires_permission=True))

    decision = PermissionService("default").decide(tool, {"metadata": {"permission_mode": "default"}}, {})

    assert decision.decision == "ask"


def test_runtime_bypass_permission_mode_allows_mutating_tool_permission() -> None:
    tool = ToolStub(ToolPermissionMetadata(action="write", risk="medium", requires_permission=True))

    decision = PermissionService("default").decide(tool, {"metadata": {"permission_mode": "bypass_read_only"}}, {})

    assert decision.decision == "allow"
    assert "bypass_read_only" in decision.reason
