"""Graph-owned hook lifecycle helpers."""

from __future__ import annotations

from typing import Any

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.hooks import apply_hook_results
from langgraph_agent_blueprint.models import HookContext, HookPoint


LIST_APPEND_KEYS = {
    "ui_events",
    "errors",
    "tool_results",
    "messages",
    "child_runs",
    "artifacts",
    "exported_outputs",
    "permission_decisions",
}
DICT_MERGE_KEYS = {
    "metadata",
    "hooks_state",
    "context_status",
    "memory",
    "usage",
    "plugin_state",
    "mcp_state",
    "permissions",
    "plan_mode",
}


def run_hook_point(deps: AppDependencies, state: dict[str, Any], hook_point: HookPoint, **overrides: Any) -> dict[str, Any]:
    """Run hooks for a graph lifecycle point and return a controlled state update."""

    context = HookContext(
        session_id=str(state.get("session_id") or "unknown"),
        thread_id=state.get("thread_id"),
        project_root=state.get("project_root"),
        cwd=state.get("cwd"),
        hook_point=hook_point,
        input_text=state.get("input_text"),
        active_tool=overrides.get("active_tool"),
        active_skill=overrides.get("active_skill") or state.get("active_skill"),
        active_command=overrides.get("active_command") or state.get("active_command"),
        permission_request=overrides.get("permission_request"),
        metadata={
            "available_tool_count": len(state.get("available_tools", {})),
            "available_skill_count": len(state.get("available_skills", {})),
            **(overrides.get("metadata") or {}),
        },
    )
    summary = deps.hook_service.run(context)
    applied = apply_hook_results(state, summary.results)
    base = {
        "hooks_state": {
            **state.get("hooks_state", {}),
            "last_hook_point": hook_point,
            "last_hook_count": len(summary.results),
        },
        "ui_events": summary.events,
    }
    return merge_updates(base, applied)


def merge_updates(*updates: dict[str, Any]) -> dict[str, Any]:
    """Merge graph node updates with append/merge semantics for known reducer fields."""

    merged: dict[str, Any] = {}
    for update in updates:
        for key, value in update.items():
            if value is None and key not in {"pending_confirmation", "final_response", "active_skill"}:
                continue
            if key in LIST_APPEND_KEYS:
                merged.setdefault(key, [])
                merged[key].extend(value or [])
            elif key in DICT_MERGE_KEYS:
                merged[key] = {**merged.get(key, {}), **(value or {})}
            else:
                merged[key] = value
    return merged


def state_with_update(state: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Build a shallow state view that includes a node update for later hook context."""

    merged = dict(state)
    for key, value in update.items():
        if key in LIST_APPEND_KEYS:
            merged[key] = [*merged.get(key, []), *(value or [])]
        elif key in DICT_MERGE_KEYS:
            merged[key] = {**merged.get(key, {}), **(value or {})}
        else:
            merged[key] = value
    return merged


def hook_blocked(update: dict[str, Any]) -> bool:
    """Return whether a hook update blocked normal node behavior."""

    return bool(update.get("metadata", {}).get("hook_blocked") or update.get("final_response"))
