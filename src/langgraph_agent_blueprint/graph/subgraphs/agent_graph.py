"""LangGraph subgraph that executes model-callable agent requests as child graph runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.state import AssistantState
from langgraph_agent_blueprint.models import (
    ChildRunMetadata,
    SubagentRequest,
    SubagentResult,
    ToolCall,
    ToolResult,
    dump_model,
    event,
    tool_result_to_tool_message,
    validate_list,
)
from langgraph_agent_blueprint.tools import AgentInput


def _agent_node(state: dict[str, Any], deps: AppDependencies) -> dict[str, Any]:
    calls = validate_list(ToolCall, state.get("pending_tool_calls", []))
    if not calls:
        return {}
    call = calls[0]
    try:
        request = AgentInput.model_validate(call.args).to_request()
    except Exception as exc:
        return _tool_error(call, f"Invalid subagent request: {exc}", "SubagentRequestError")
    depth = int((state.get("metadata") or {}).get("subagent_depth", 0))
    if depth >= deps.agent_service.max_depth:
        return _tool_error(call, "Subagent recursion depth exceeded.", "SubagentDepthExceeded")
    try:
        metadata = deps.agent_service.create_child_metadata(state, request)
        child_state = deps.agent_service.create_child_state(state, request, metadata, deps.tool_registry)
    except Exception as exc:
        return _tool_error(call, f"Could not create subagent state: {exc}", "SubagentStateError")
    started_event = event(
        "subagent_started",
        session_id=state.get("session_id"),
        child_run_id=metadata.child_run_id,
        parent_session_id=metadata.parent_session_id,
        child_session_id=metadata.child_session_id,
        child_thread_id=metadata.child_thread_id,
        name=metadata.name,
        purpose=metadata.purpose,
        status="running",
    )
    child_result = _run_child_graph(deps, child_state, request)
    metadata, result, finished_event = _summarize_child_run(state, metadata, request, child_result)
    child_events = child_result.get("ui_events", []) if isinstance(child_result, dict) else []
    forwarded_events = [
        event(
            "subagent_event",
            session_id=state.get("session_id"),
            child_run_id=metadata.child_run_id,
            child_event_type=item.get("type"),
            child_event=item,
        )
        for item in child_events
    ]
    metadata_payload = dump_model(metadata)
    result_payload = dump_model(result)
    child_record = {
        "id": metadata.child_run_id,
        "status": metadata.status,
        "metadata": metadata_payload,
        "result": result_payload,
        "result_summary": result.summary,
        "result_status": result.status,
    }
    tool_result = ToolResult(
        id=call.id,
        name=call.name,
        status="ok" if result.status == "ok" else "error",
        content=result.summary,
        metadata={
            "child_run_id": metadata.child_run_id,
            "child_session_id": metadata.child_session_id,
            "child_thread_id": metadata.child_thread_id,
            "name": metadata.name,
            "purpose": metadata.purpose,
            "status": metadata.status,
        },
        output={"metadata": metadata_payload, "result": result_payload},
        error=result.errors[0] if result.errors else None,
    )
    parent_metadata = dict(state.get("metadata", {}))
    refs = list(parent_metadata.get("child_run_refs", []))
    if metadata.child_run_id not in refs:
        refs.append(metadata.child_run_id)
    parent_metadata["child_run_refs"] = refs
    persistence_events: list[dict[str, Any]] = []
    try:
        deps.session_storage.save_child_run(
            state["project_root"],
            state["session_id"],
            metadata_payload,
            result_payload,
            child_events,
        )
    except Exception as exc:
        persistence_events.append(
            event(
                "subagent_event",
                session_id=state.get("session_id"),
                severity="warning",
                child_run_id=metadata.child_run_id,
                child_event_type="child_run_persistence_error",
                error_type=exc.__class__.__name__,
                message=str(exc),
            )
        )
    return {
        "metadata": parent_metadata,
        "child_runs": [child_record],
        "pending_tool_calls": [],
        "tool_results": [dump_model(tool_result)],
        "messages": [tool_result_to_tool_message(tool_result)],
        "ui_events": [started_event, *forwarded_events, *persistence_events, finished_event],
    }


def _run_child_graph(deps: AppDependencies, child_state: dict[str, Any], request: SubagentRequest) -> dict[str, Any]:
    """Run the same compiled main graph for an isolated child state."""

    from langgraph_agent_blueprint.graph.builder import build_main_graph
    from langgraph_agent_blueprint.graph.checkpoints import default_checkpointer

    app = build_main_graph(deps).compile(checkpointer=default_checkpointer())
    config = {
        "configurable": {"thread_id": child_state["thread_id"]},
        "recursion_limit": max(12, request.max_turns * 8),
    }
    result = app.invoke(child_state, config)
    return result if isinstance(result, dict) else {"final_response": str(result)}


def _summarize_child_run(
    parent_state: dict[str, Any],
    metadata: ChildRunMetadata,
    request: SubagentRequest,
    child_result: dict[str, Any],
) -> tuple[ChildRunMetadata, SubagentResult, dict[str, Any]]:
    completed_at = datetime.now(timezone.utc).isoformat()
    interrupt_payload = child_result.get("__interrupt__")
    if interrupt_payload:
        summary = "Subagent side-effect tool call requires approval; nested approval is not supported in this run."
        updated_metadata = metadata.model_copy(
            update={
                "status": "failed",
                "completed_at": completed_at,
                "metadata": {**metadata.metadata, "allowed_tools": _child_allowed_tools(child_result), "interrupted": True},
            }
        )
        result = SubagentResult(
            child_run_id=metadata.child_run_id,
            status="error",
            summary=summary,
            errors=[{"type": "NestedApprovalUnsupported", "message": summary}],
            metadata={"name": request.name, "interrupted": True},
        )
        return updated_metadata, result, _finished_event(parent_state, updated_metadata, result, "subagent_error")
    errors = child_result.get("errors", []) if isinstance(child_result.get("errors"), list) else []
    status = "failed" if errors else "completed"
    result_status = "error" if errors else "ok"
    final_response = str(child_result.get("final_response") or "")
    summary = final_response or _last_tool_result_content(child_result) or "Subagent completed without a final response."
    updated_metadata = metadata.model_copy(
        update={
            "status": status,
            "completed_at": completed_at,
            "metadata": {**metadata.metadata, "allowed_tools": _child_allowed_tools(child_result)},
        }
    )
    result = SubagentResult(
        child_run_id=metadata.child_run_id,
        status=result_status,
        summary=summary,
        final_response=final_response or None,
        tool_results=list(child_result.get("tool_results", [])) if isinstance(child_result.get("tool_results"), list) else [],
        artifacts=list(child_result.get("artifacts", [])) if isinstance(child_result.get("artifacts"), list) else [],
        errors=errors,
        metadata={"name": request.name},
    )
    return updated_metadata, result, _finished_event(parent_state, updated_metadata, result, "subagent_finished" if result_status == "ok" else "subagent_error")


def _finished_event(parent_state: dict[str, Any], metadata: ChildRunMetadata, result: SubagentResult, event_type: str) -> dict[str, Any]:
    return event(
        event_type,
        session_id=parent_state.get("session_id"),
        child_run_id=metadata.child_run_id,
        parent_session_id=metadata.parent_session_id,
        child_session_id=metadata.child_session_id,
        child_thread_id=metadata.child_thread_id,
        name=metadata.name,
        purpose=metadata.purpose,
        status=metadata.status,
        summary=result.summary,
    )


def _last_tool_result_content(child_result: dict[str, Any]) -> str:
    tool_results = child_result.get("tool_results", [])
    if isinstance(tool_results, list) and tool_results:
        last = tool_results[-1]
        if isinstance(last, dict):
            return str(last.get("content") or "")
    return ""


def _child_allowed_tools(child_result: dict[str, Any]) -> list[str]:
    metadata = child_result.get("metadata", {}) if isinstance(child_result.get("metadata"), dict) else {}
    allowed = metadata.get("allowed_tools_override")
    return [str(item) for item in allowed] if isinstance(allowed, list) else []


def _tool_error(call: ToolCall, message: str, error_type: str) -> dict[str, Any]:
    result = ToolResult(
        id=call.id,
        name=call.name,
        status="error",
        content=message,
        metadata={"error_type": error_type},
        error={"type": error_type, "message": message},
    )
    return {
        "pending_tool_calls": [],
        "tool_results": [dump_model(result)],
        "messages": [tool_result_to_tool_message(result)],
        "ui_events": [event("subagent_error", id=call.id, reason=message, error_type=error_type)],
    }


def build_agent_graph(deps: AppDependencies) -> StateGraph:
    graph = StateGraph(AssistantState)
    graph.add_node("agent_run", lambda state: _agent_node(state, deps))
    graph.add_edge(START, "agent_run")
    graph.add_edge("agent_run", END)
    return graph
