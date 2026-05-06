"""Conditional-edge routing functions for command, tool, permission, and compaction paths."""

from __future__ import annotations

from typing import Any


def route_after_command(state: dict[str, Any]) -> str:
    """Choose the next graph node after command routing based on command side effects."""

    if state.get("errors"):
        return "error_recovery"
    if state.get("metadata", {}).get("compact_requested"):
        return "compact_decision"
    if state.get("command_handled") or state.get("final_response"):
        return "persist_session"
    if state.get("active_skill"):
        return "skill_graph"
    return "context_builder"


def route_after_tool_router(state: dict[str, Any]) -> str:
    return state.get("metadata", {}).get("tool_route", "no_tools")


def route_after_permission(state: dict[str, Any]) -> str:
    return state.get("metadata", {}).get("tool_route", "execute")


def route_after_tool_execution(state: dict[str, Any]) -> str:
    if state.get("errors"):
        return "error_recovery"
    return "model_call"


def route_after_compact_decision(state: dict[str, Any]) -> str:
    return "compact_context" if state.get("metadata", {}).get("compact_route") == "compact" else "persist_session"
