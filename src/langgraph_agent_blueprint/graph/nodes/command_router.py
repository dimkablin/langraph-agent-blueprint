"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from langgraph_agent_blueprint.commands.parser import parse_slash_command
from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models.messages import event


def command_router_node(state: dict, deps: AppDependencies) -> dict:
    """Parse and execute slash commands, translating command results into graph state updates.

    Local commands finish the turn, prompt commands append a user message, skill commands set
    `active_skill`, and session-style commands can trigger storage/export/diagnostic side effects.
    """

    parsed = parse_slash_command(state.get("input_text", ""))
    if not parsed:
        return {"command_handled": False}
    name, args = parsed.name, parsed.args
    command = deps.command_registry.find(name)
    if command is None:
        return {
            "command_handled": True,
            "active_command": parsed.model_dump(mode="json"),
            "final_response": f"Unknown command /{name}. Use /help to list available commands.",
            "ui_events": [event("command_finished", name=name, status="unknown")],
        }
    command_state = {**state, "available_commands": state.get("available_commands", deps.command_registry.snapshot())}
    if name == "memory":
        command_state["memory"] = deps.memory_service.load_memory(state.get("project_root"), state.get("session_id"))
    result = command.execute(args, command_state)
    update: dict = {
        "active_command": {"name": name, "args": args, "type": command.type},
        "command_handled": result.handled,
        "ui_events": [event("command_started", name=name), event("command_finished", name=name, handled=result.handled)],
    }
    metadata = {**state.get("metadata", {}), **(result.metadata or {})}
    if result.response is not None:
        update["final_response"] = result.response
    if name == "doctor" and result.metadata and result.metadata.get("doctor_requested"):
        diagnostics = deps.diagnostics_service.run()
        diagnostics["mcp"] = deps.mcp_service.diagnostics()
        diagnostics["langfuse"] = deps.observability_service.status()
        update["final_response"] = json.dumps(diagnostics, ensure_ascii=False, indent=2)
        metadata["diagnostics"] = diagnostics
    if name == "export" and result.metadata and result.metadata.get("export_requested"):
        export = deps.export_service.export_transcript(state["session_id"], state.get("messages", []), result.metadata.get("format", "markdown"))
        exported = {"path": str(export.path), "format": result.metadata.get("format", "markdown")}
        update["final_response"] = f"Exported transcript to {export.path}"
        update["exported_outputs"] = [exported]
        update["ui_events"].append(event("export_finished", **exported))
    if name == "resume" and result.metadata and result.metadata.get("resume"):
        target = str(result.metadata["resume"])
        if target == "latest":
            sessions = deps.session_service.list(state.get("project_root"))
            target = str(sessions[0]["session_id"]) if sessions else ""
        if target:
            try:
                loaded = deps.session_service.resume(state["project_root"], target)
            except (FileNotFoundError, OSError):
                update["final_response"] = f"Session not found: {target}"
            else:
                update["session_id"] = target
                update["messages"] = [RemoveMessage(id=REMOVE_ALL_MESSAGES), *loaded.get("messages", [])]
                update["todos"] = loaded.get("todos", [])
                update["memory"] = loaded.get("memory", {})
                update["usage"] = loaded.get("usage", {})
                metadata.update(loaded.get("metadata", {}))
                metadata["resumed_session"] = target
                update["final_response"] = f"Resumed session: {target}"
        else:
            update["final_response"] = "No sessions found to resume."
    if name == "memory":
        update["memory"] = command_state.get("memory", {})
    if result.prompt is not None:
        update["messages"] = [HumanMessage(content=result.prompt)]
    if result.skill is not None:
        update["active_skill"] = result.skill
    update["metadata"] = metadata
    if metadata.get("clear_messages"):
        update["messages"] = [RemoveMessage(id=REMOVE_ALL_MESSAGES)]
    return update
