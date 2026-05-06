"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, ToolMessage

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event
from claude_code_langgraph.skills.args import SkillArgumentValidationError


def skill_router_node(state: dict, deps: AppDependencies) -> dict:
    """Resolve the active skill and prepare graph state for skill-scoped model/tool execution.

    Explicit `/skill` calls become a rendered prompt; model-invoked SkillTool calls also receive a
    matching ToolMessage. The `remember` skill has a direct durable-memory path.
    """

    active = state.get("active_skill")
    if not active:
        return {}
    raw_args = active.get("args", "")
    try:
        result = deps.skill_service.invoke(active["name"], raw_args, state)
    except SkillArgumentValidationError as exc:
        return _skill_validation_error_update(state, active, exc)
    except KeyError as exc:
        return _skill_lookup_error_update(state, active, str(exc))
    skill_args = result["args"]
    metadata = {
        **state.get("metadata", {}),
        "allowed_tools_override": result.get("allowed_tools", []),
        "active_skill_name": active["name"],
        "skill_invocation": {
            "name": active["name"],
            "args": skill_args,
            "source_path": result.get("source_path"),
            "allowed_tools": result.get("allowed_tools", []),
        },
    }
    messages = []
    events = [event("skill_started", name=active["name"])]
    final_response = None
    memory = None
    if active["name"] == "remember":
        typed_args = result["typed_args"]
        scope, text = typed_args["scope"], typed_args["text"]
        path = deps.memory_service.remember(scope, text, state.get("session_id"))
        memory = deps.memory_service.load_memory(state.get("project_root"), state.get("session_id"))
        final_response = f"Remembered in {scope} memory: {text}"
        events.append(event("memory_updated", scope=scope, path=str(path)))
    else:
        messages.append(HumanMessage(content=result["prompt"]))
    if active.get("tool_call_id"):
        messages.insert(
            0,
            ToolMessage(
                content=json.dumps(
                    {"skill": active["name"], "status": "prepared", "allowed_tools": result.get("allowed_tools", [])},
                    ensure_ascii=False,
                ),
                tool_call_id=str(active["tool_call_id"]),
            ),
        )
    events.append(event("skill_finished", name=active["name"]))
    update = {
        "active_skill": {"name": active["name"], "args": skill_args, "result": result},
        "messages": messages,
        "metadata": metadata,
        "ui_events": events,
    }
    if final_response is not None:
        update["final_response"] = final_response
    if memory is not None:
        update["memory"] = memory
    return update


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
