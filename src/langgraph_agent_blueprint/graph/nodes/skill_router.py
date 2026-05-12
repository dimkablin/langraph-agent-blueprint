"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, ToolMessage

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models import AgentActivityEvent, AgentActivitySource, event
from langgraph_agent_blueprint.skills import SkillEffect, apply_skill_effects
from langgraph_agent_blueprint.skills.args import SkillArgumentValidationError
from langgraph_agent_blueprint.utils.activity import normalize_activity_namespace, safe_activity_data


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
    requested_name = str(active.get("name") or "unknown")
    loading_event = event(
        "skill_started",
        name=requested_name,
        activity=_skill_activity(
            activity_type=f"skill.{normalize_activity_namespace(requested_name)}.loading",
            status="running",
            title="Loading skill",
            name=requested_name,
            requested_name=requested_name,
            summary=f"Loading skill {requested_name}.",
            data={"name": requested_name, "requested_name": requested_name},
        ).model_dump(mode="json"),
    )
    try:
        result = deps.skill_service.invoke(active["name"], raw_args, current)
    except SkillArgumentValidationError as exc:
        update = _skill_validation_error_update(current, active, exc, loading_event)
        post_update = run_hook_point(deps, state_with_update(current, update), "post_skill", active_skill=active)
        return merge_updates(pre_update, update, post_update)
    except KeyError as exc:
        update = _skill_lookup_error_update(current, active, str(exc), loading_event)
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
    loaded_activity = _skill_activity_from_result(
        result,
        activity_type=f"skill.{normalize_activity_namespace(skill_name)}.loaded",
        status="success",
        title="Skill loaded",
        summary=f"Loaded skill {skill_name}.",
    )
    activated_activity = _skill_activity_from_result(
        result,
        activity_type=f"skill.{normalize_activity_namespace(skill_name)}.activated",
        status="success",
        title="Skill activated",
        summary=f"Activated skill {skill_name}.",
    )
    events = [
        loading_event,
        event("agent_activity", activity=loaded_activity.model_dump(mode="json")),
    ]
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
    events.append(event("skill_finished", name=skill_name, activity=activated_activity.model_dump(mode="json")))
    update = {
        "active_skill": {"name": skill_name, "requested_name": active["name"], "args": skill_args, "result": result},
        "messages": messages,
        "metadata": metadata,
        "ui_events": events,
    }
    update = merge_updates(update, effect_update)
    post_update = run_hook_point(deps, state_with_update(current, update), "post_skill", active_skill=update["active_skill"])
    return merge_updates(pre_update, update, post_update)


def _skill_validation_error_update(state: dict, active: dict, exc: SkillArgumentValidationError, loading_event: dict) -> dict:
    """Return a structured graph update for invalid typed skill args."""

    content = f"Invalid arguments for skill {exc.skill_name}: {exc.errors}"
    return _skill_error_update(
        state,
        active,
        content,
        {"error_type": "skill_args_validation", "errors": exc.errors, "skill": exc.skill_name},
        loading_event,
    )


def _skill_lookup_error_update(state: dict, active: dict, message: str, loading_event: dict) -> dict:
    """Return a structured graph update for unknown skill names."""

    return _skill_error_update(state, active, message, {"error_type": "unknown_skill", "skill": active.get("name")}, loading_event)


def _skill_error_update(state: dict, active: dict, content: str, metadata: dict, loading_event: dict) -> dict:
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
    skill_name = str(active.get("name") or "unknown")
    failed = _skill_activity(
        activity_type=f"skill.{normalize_activity_namespace(skill_name)}.failed",
        status="error",
        title="Skill failed",
        name=skill_name,
        requested_name=skill_name,
        summary=content,
        data={"name": skill_name, "requested_name": skill_name, "error_type": metadata.get("error_type")},
    )
    return {
        "active_skill": {"name": active.get("name"), "args": active.get("args", ""), "error": metadata},
        "pending_tool_calls": [],
        "tool_results": [result],
        "messages": messages,
        "final_response": content if not tool_call_id else None,
        "ui_events": [loading_event, event("skill_finished", name=active.get("name"), status="error", activity=failed.model_dump(mode="json"))],
    }


def _skill_activity_from_result(result: dict, *, activity_type: str, status: str, title: str, summary: str) -> AgentActivityEvent:
    return _skill_activity(
        activity_type=activity_type,
        status=status,
        title=title,
        name=str(result.get("name") or "unknown"),
        requested_name=str(result.get("requested_name") or result.get("name") or "unknown"),
        summary=summary,
        data={
            "name": result.get("name"),
            "requested_name": result.get("requested_name"),
            "description": result.get("description"),
            "allowed_tools": result.get("allowed_tools", []),
            "args_schema": result.get("args_schema"),
            "model": result.get("model"),
            "effort": result.get("effort"),
            "context": result.get("context"),
            "agent": result.get("agent"),
            "source_type": result.get("source_type"),
            "plugin_name": result.get("plugin_name"),
        },
    )


def _skill_activity(
    *,
    activity_type: str,
    status: str,
    title: str,
    name: str,
    requested_name: str,
    summary: str,
    data: dict,
) -> AgentActivityEvent:
    return AgentActivityEvent(
        id=f"activity_skill_{normalize_activity_namespace(requested_name)}_{activity_type.rsplit('.', 1)[-1]}",
        type=activity_type,
        source=AgentActivitySource(kind="skill", name=name, component="SkillInvocationService"),
        category="skill",
        status=status,  # type: ignore[arg-type]
        title=title,
        summary=summary,
        data=safe_activity_data(data),
    )
