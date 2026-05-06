"""Tests for typed command and permission boundary contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from langgraph_agent_blueprint.commands.parser import parse_slash_command
from langgraph_agent_blueprint.models.commands import CommandResult, ParsedCommand
from langgraph_agent_blueprint.models.permissions import PermissionDecision, PermissionRequest
from langgraph_agent_blueprint.services.permission_service import PermissionService
from langgraph_agent_blueprint.tools.registry import build_core_tool_registry


def test_parse_slash_command_returns_typed_command_payload():
    parsed = parse_slash_command("/skill verify run tests")

    assert parsed == ParsedCommand(name="skill", args="verify run tests", raw="/skill verify run tests", command_type="skill")
    assert parse_slash_command("normal chat") is None


def test_command_result_infers_final_response_route():
    result = CommandResult(True, "ok")

    assert result.route == "finalize"
    assert result.final_response == "ok"


def test_permission_payload_is_typed_request(tmp_path):
    tool = build_core_tool_registry(project_root=tmp_path).get("write_file")
    payload = PermissionService.confirmation_payload(
        {"id": "call_1", "name": "write_file", "args": {"path": "x.txt", "content": "x"}},
        tool,
        "write_file requires approval",
    )

    request = PermissionRequest.model_validate(payload.model_dump(mode="json"))

    assert request.tool_call_id == "call_1"
    assert request.tool_name == "write_file"
    assert request.action == "write"
    assert request.risk == "medium"


def test_permission_decision_validates_resume_payload():
    approved = PermissionDecision.model_validate({"tool_call_id": "call_1", "decision": "approved"})

    assert approved.decision == "approved"
    with pytest.raises(ValidationError):
        PermissionDecision.model_validate({"tool_call_id": "call_1", "decision": "maybe"})
