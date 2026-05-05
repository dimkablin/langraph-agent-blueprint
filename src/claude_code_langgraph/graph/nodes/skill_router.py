"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, ToolMessage

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def skill_router_node(state: dict, deps: AppDependencies) -> dict:
    active = state.get("active_skill")
    if not active:
        return {}
    result = deps.skill_service.invoke(active["name"], active.get("args", ""), state)
    metadata = {
        **state.get("metadata", {}),
        "allowed_tools_override": result.get("allowed_tools", []),
        "active_skill_name": active["name"],
        "skill_invocation": {
            "name": active["name"],
            "args": active.get("args", ""),
            "source_path": result.get("source_path"),
            "allowed_tools": result.get("allowed_tools", []),
        },
    }
    messages = []
    events = [event("skill_started", name=active["name"])]
    final_response = None
    memory = None
    if active["name"] == "remember":
        scope, text = _parse_memory_args(active.get("args", ""))
        path = deps.memory_service.remember(scope, text)
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
        "active_skill": {"name": active["name"], "args": active.get("args", ""), "result": result},
        "messages": messages,
        "metadata": metadata,
        "ui_events": events,
    }
    if final_response is not None:
        update["final_response"] = final_response
    if memory is not None:
        update["memory"] = memory
    return update


def _parse_memory_args(args: str) -> tuple[str, str]:
    stripped = args.strip()
    if ":" in stripped:
        maybe_scope, text = stripped.split(":", 1)
        scope = maybe_scope.strip().lower()
        if scope in {"user", "project", "session"} and text.strip():
            return scope, text.strip()
    return "project", stripped
