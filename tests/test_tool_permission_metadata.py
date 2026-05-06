"""Tests for metadata-driven tool classification."""

from __future__ import annotations

from claude_code_langgraph.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata
from claude_code_langgraph.tools.registry import build_core_tool_registry


def test_every_core_tool_declares_permission_and_runtime_metadata(tmp_path):
    registry = build_core_tool_registry(project_root=tmp_path)

    expected = {
        "read_file": ("read", "low", True, False, True, "file", "execute"),
        "write_file": ("write", "medium", False, True, False, "file", "execute"),
        "edit_file": ("edit", "medium", False, True, False, "file", "execute"),
        "notebook_read": ("read", "low", True, False, True, "notebook", "execute"),
        "notebook_edit": ("edit", "medium", False, True, False, "notebook", "execute"),
        "glob": ("read", "low", True, False, True, "search", "execute"),
        "grep": ("read", "low", True, False, True, "search", "execute"),
        "bash": ("shell", "high", False, True, False, "shell", "execute"),
        "powershell": ("shell", "high", False, True, False, "shell", "execute"),
        "web_fetch": ("network", "medium", False, True, False, "network", "execute"),
        "web_search": ("network", "medium", False, True, False, "network", "execute"),
        "todo_write": ("todo", "low", False, False, True, "todo", "execute"),
        "skill": ("skill", "low", False, False, True, "skill", "skill_graph"),
        "agent": ("agent", "medium", False, False, True, "agent", "agent_graph"),
        "diagnostics": ("diagnostics", "low", True, False, True, "diagnostics", "execute"),
    }

    for name, (action, risk, read_only, requires_permission, plan_allowed, kind, route) in expected.items():
        tool = registry.get(name)
        assert isinstance(tool.permission, ToolPermissionMetadata)
        assert isinstance(tool.runtime, ToolRuntimeMetadata)
        assert tool.permission.action == action
        assert tool.permission.risk == risk
        assert tool.permission.is_read_only is read_only
        assert tool.permission.requires_permission is requires_permission
        assert tool.permission.allowed_in_plan_mode is plan_allowed
        assert tool.runtime.kind == kind
        assert tool.runtime.route == route


def test_tool_registry_snapshot_includes_metadata_contracts(tmp_path):
    snapshot = build_core_tool_registry(project_root=tmp_path).snapshot()

    read_file = snapshot["read_file"]
    assert read_file["permission"]["action"] == "read"
    assert read_file["runtime"]["kind"] == "file"
    assert read_file["is_read_only"] is True
    assert read_file["requires_permission"] is False
