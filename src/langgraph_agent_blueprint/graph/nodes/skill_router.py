"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, ToolMessage

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models import event
from langgraph_agent_blueprint.skills import SkillEffect, apply_skill_effects
from langgraph_agent_blueprint.skills.args import SkillArgumentValidationError


def skill_router_node(state: dict, deps: AppDependencies) -> dict:
    """Resolve the active skill and prepare graph state for skill-scoped model/tool execution.

    Explicit `/skill` calls become a rendered prompt; model-invoked SkillTool calls also receive a
    matching ToolMessage. Durable side effects are applied through typed skill effects.
    """

    active = state.get("active_skill")
    if not active:
        return {}
    pre_update = run_hook_point(deps, state, "pre_skill", active_skill=active)
    if hook_blocked(pre_update):
        return pre_update
    current = state_with_update(state, pre_update)
    raw_args = active.get("args", "")
    try:
        result = deps.skill_service.invoke(active["name"], raw_args, current)
    except SkillArgumentValidationError as exc:
        update = _skill_validation_error_update(current, active, exc)
        post_update = run_hook_point(deps, state_with_update(current, update), "post_skill", active_skill=active)
        return merge_updates(pre_update, update, post_update)
    except KeyError as exc:
        update = _skill_lookup_error_update(current, active, str(exc))
        post_update = run_hook_point(deps, state_with_update(current, update), "post_skill", active_skill=active)
        return merge_updates(pre_update, update, post_update)
    skill_name = result["name"]
    skill_args = result["args"]
    skill_invocations = list(dict.fromkeys([*current.get("metadata", {}).get("skill_invocations", []), skill_name]))
    metadata = {
        **current.get("metadata", {}),
        "allowed_tools_override": result.get("allowed_tools", []),
        "active_skill_name": skill_name,
        "skill_invocations": skill_invocations,
        "skill_invocation": {
            "name": skill_name,
            "requested_name": active["name"],
            "args": skill_args,
            "source_path": result.get("source_path"),
            "allowed_tools": result.get("allowed_tools", []),
        },
    }
    messages = []
    events = [event("skill_started", name=skill_name)]
    effects = [SkillEffect.model_validate(item) for item in result.get("effects", [])]
    effect_update = apply_skill_effects(effects, current, deps)
    if not effect_update.get("final_response"):
        messages.append(HumanMessage(content=result["prompt"]))
    if active.get("tool_call_id"):
        messages.insert(
            0,
            ToolMessage(
                content=json.dumps(
                    {"skill": skill_name, "status": "prepared", "allowed_tools": result.get("allowed_tools", [])},
                    ensure_ascii=False,
                ),
                tool_call_id=str(active["tool_call_id"]),
            ),
        )
    events.append(event("skill_finished", name=skill_name))
    update = {
        "active_skill": {"name": skill_name, "requested_name": active["name"], "args": skill_args, "result": result},
        "messages": messages,
        "metadata": metadata,
        "ui_events": events,
    }
    update = merge_updates(update, effect_update)
    post_update = run_hook_point(deps, state_with_update(current, update), "post_skill", active_skill=update["active_skill"])
    return merge_updates(pre_update, update, post_update)


def _skill_validation_error_update(state: dict, active: dict, exc: SkillArgumentValidationError) -> dict:
    """Return a structured graph update for invalid typed skill args."""

    content = f"Invalid arguments for skill {exc.skill_name}: {exc.errors}"
    return _skill_error_update(
        state,
        active,
        content,
        {"error_type": "skill_args_validation", "errors": exc.errors, "skill": exc.skill_name},
    )


def _skill_lookup_error_update(state: dict, active: dict, message: str) -> dict:
    """Return a structured graph update for unknown skill names."""

    return _skill_error_update(state, active, message, {"error_type": "unknown_skill", "skill": active.get("name")})


def _skill_error_update(state: dict, active: dict, content: str, metadata: dict) -> dict:
    tool_call_id = active.get("tool_call_id")
    result = {"id": tool_call_id or "skill", "name": "skill", "status": "error", "content": content, "metadata": metadata}
    messages = []
    if tool_call_id:
        messages.append(
            ToolMessage(
                content=json.dumps({"name": "skill", "status": "error", "content": content, "metadata": metadata}, ensure_ascii=False),
                tool_call_id=str(tool_call_id),
            )
        )
    return {
        "active_skill": {"name": active.get("name"), "args": active.get("args", ""), "error": metadata},
        "pending_tool_calls": [],
        "tool_results": [result],
        "messages": messages,
        "final_response": content if not tool_call_id else None,
        "ui_events": [event("skill_started", name=active.get("name")), event("skill_finished", name=active.get("name"), status="error")],
    }
