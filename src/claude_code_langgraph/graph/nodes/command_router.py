from __future__ import annotations

from langchain_core.messages import HumanMessage

from claude_code_langgraph.commands.parser import parse_slash_command
from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def command_router_node(state: dict, deps: AppDependencies) -> dict:
    parsed = parse_slash_command(state.get("input_text", ""))
    if not parsed:
        return {"command_handled": False}
    name, args = parsed
    command = deps.command_registry.find(name)
    if command is None:
        return {
            "command_handled": True,
            "active_command": {"name": name, "args": args, "type": "unknown"},
            "final_response": f"Unknown command /{name}. Use /help to list available commands.",
            "ui_events": [event("command_finished", name=name, status="unknown")],
        }
    command_state = {**state, "available_commands": state.get("available_commands", deps.command_registry.snapshot())}
    result = command.execute(args, command_state)
    update: dict = {
        "active_command": {"name": name, "args": args, "type": command.type},
        "command_handled": result.handled,
        "ui_events": [event("command_started", name=name), event("command_finished", name=name, handled=result.handled)],
    }
    metadata = {**state.get("metadata", {}), **(result.metadata or {})}
    if result.response is not None:
        update["final_response"] = result.response
    if result.prompt is not None:
        update["messages"] = [HumanMessage(content=result.prompt)]
    if result.skill is not None:
        update["active_skill"] = result.skill
    update["metadata"] = metadata
    if metadata.get("clear_messages"):
        update["messages"] = []
    return update

