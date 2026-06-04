"""LangGraph subgraph that executes model-callable agent requests as child graph runs."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Lock
from typing import Any

from langgraph.config import get_stream_writer
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


MAX_PARALLEL_SUBAGENT_RUNS = 4
SUBAGENT_EVENT_DRAIN_INTERVAL_SECONDS = 0.05


@dataclass(frozen=True)
class _PreparedAgentCall:
    call: ToolCall
    request: SubagentRequest
    metadata: ChildRunMetadata
    child_state: dict[str, Any]
    started_event: dict[str, Any]


class _AgentCallPreparationError(Exception):
    def __init__(self, message: str, error_type: str) -> None:
        super().__init__(message)
        self.error_type = error_type


def _agent_node(state: dict[str, Any], deps: AppDependencies) -> dict[str, Any]:
    calls = validate_list(ToolCall, state.get("pending_tool_calls", []))
    if not calls:
        return {}
    writer = _stream_writer(state)
    metadata = dict(state.get("metadata", {}))
    if len(calls) > 1:
        return _run_agent_calls_concurrently(state, deps, calls, metadata, writer)
    child_runs: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    messages: list[Any] = []
    ui_events: list[dict[str, Any]] = []
    for call in calls:
        update = _run_agent_call(state, deps, call, metadata, writer)
        metadata = dict(update.get("metadata", metadata))
        child_runs.extend(update.get("child_runs", []))
        tool_results.extend(update.get("tool_results", []))
        messages.extend(update.get("messages", []))
        ui_events.extend(update.get("ui_events", []))
    return {
        "metadata": metadata,
        "child_runs": child_runs,
        "pending_tool_calls": [],
        "tool_results": tool_results,
        "messages": messages,
        "ui_events": ui_events,
    }


def _run_agent_calls_concurrently(
    state: dict[str, Any],
    deps: AppDependencies,
    calls: list[ToolCall],
    metadata: dict[str, Any],
    writer: Any | None,
) -> dict[str, Any]:
    event_queue: Queue[dict[str, Any]] = Queue()
    streamed_events: list[dict[str, Any]] = []
    streamed_event_ids: set[str] = set()
    persistence_lock = Lock()
    thread_writer = event_queue.put if writer is not None else None
    results: dict[int, dict[str, Any]] = {}
    prepared_calls: list[tuple[int, _PreparedAgentCall]] = []

    def emit_event(item: dict[str, Any]) -> None:
        streamed_events.append(item)
        event_id = str(item.get("id") or "")
        if event_id:
            streamed_event_ids.add(event_id)
        deps.run_event_stream_service.publish(state.get("thread_id"), item)
        writer(item)

    for index, call in enumerate(calls):
        try:
            prepared_calls.append((index, _prepare_agent_call(state, deps, call, metadata)))
        except _AgentCallPreparationError as exc:
            update = _tool_error(call, str(exc), exc.error_type)
            results[index] = update
            if writer is not None:
                for item in update.get("ui_events", []):
                    emit_event(item)

    if writer is not None:
        for _, prepared in prepared_calls:
            emit_event(prepared.started_event)

    def drain_events() -> None:
        if writer is None:
            return
        while True:
            try:
                item = event_queue.get_nowait()
            except Empty:
                break
            emit_event(item)

    if prepared_calls:
        max_workers = min(len(prepared_calls), MAX_PARALLEL_SUBAGENT_RUNS)
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="subagent") as executor:
            futures: dict[Future[dict[str, Any]], tuple[int, ToolCall]] = {
                executor.submit(
                    _run_prepared_agent_call,
                    state,
                    deps,
                    prepared,
                    metadata,
                    thread_writer,
                    persistence_lock,
                    False,
                    False,
                ): (index, prepared.call)
                for index, prepared in prepared_calls
            }
            while futures:
                done, _ = wait(
                    futures,
                    timeout=SUBAGENT_EVENT_DRAIN_INTERVAL_SECONDS,
                    return_when=FIRST_COMPLETED,
                )
                drain_events()
                for future in done:
                    index, call = futures.pop(future)
                    try:
                        results[index] = future.result()
                    except Exception as exc:
                        results[index] = _tool_error(call, f"Subagent run failed: {exc}", exc.__class__.__name__)
            drain_events()

    ordered_results = [results[index] for index in range(len(calls)) if index in results]
    child_runs: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    messages: list[Any] = []
    non_streamed_events: list[dict[str, Any]] = []
    child_run_refs = list(metadata.get("child_run_refs", []))
    for update in ordered_results:
        child_runs.extend(update.get("child_runs", []))
        tool_results.extend(update.get("tool_results", []))
        messages.extend(update.get("messages", []))
        for child_run in update.get("child_runs", []):
            child_run_id = child_run.get("id")
            if child_run_id and child_run_id not in child_run_refs:
                child_run_refs.append(child_run_id)
        for item in update.get("ui_events", []):
            event_id = str(item.get("id") or "")
            if event_id and event_id in streamed_event_ids:
                continue
            non_streamed_events.append(item)
    next_metadata = dict(metadata)
    next_metadata["child_run_refs"] = child_run_refs
    return {
        "metadata": next_metadata,
        "child_runs": child_runs,
        "pending_tool_calls": [],
        "tool_results": tool_results,
        "messages": messages,
        "ui_events": [*streamed_events, *non_streamed_events],
    }


def _prepare_agent_call(
    state: dict[str, Any],
    deps: AppDependencies,
    call: ToolCall,
    parent_metadata: dict[str, Any],
) -> _PreparedAgentCall:
    try:
        request = AgentInput.model_validate(call.args).to_request()
    except Exception as exc:
        raise _AgentCallPreparationError(f"Invalid subagent request: {exc}", "SubagentRequestError") from exc
    depth = int(parent_metadata.get("subagent_depth", 0))
    if depth >= deps.agent_service.max_depth:
        raise _AgentCallPreparationError("Subagent recursion depth exceeded.", "SubagentDepthExceeded")
    try:
        current_state = {**state, "metadata": parent_metadata}
        metadata = deps.agent_service.create_child_metadata(current_state, request)
        child_state = deps.agent_service.create_child_state(current_state, request, metadata, deps.tool_registry)
    except Exception as exc:
        raise _AgentCallPreparationError(f"Could not create subagent state: {exc}", "SubagentStateError") from exc
    started_event = event(
        "subagent_started",
        session_id=state.get("session_id"),
        child_run_id=metadata.child_run_id,
        parent_session_id=metadata.parent_session_id,
        child_session_id=metadata.child_session_id,
        child_thread_id=metadata.child_thread_id,
        agent_call_id=call.id,
        name=metadata.name,
        purpose=metadata.purpose,
        status="running",
    )
    return _PreparedAgentCall(
        call=call,
        request=request,
        metadata=metadata,
        child_state=child_state,
        started_event=started_event,
    )


def _run_agent_call(
    state: dict[str, Any],
    deps: AppDependencies,
    call: ToolCall,
    parent_metadata: dict[str, Any],
    writer: Any | None,
    persistence_lock: Lock | None = None,
    publish_direct: bool = True,
) -> dict[str, Any]:
    try:
        prepared = _prepare_agent_call(state, deps, call, parent_metadata)
    except _AgentCallPreparationError as exc:
        return _tool_error(call, str(exc), exc.error_type)
    return _run_prepared_agent_call(
        state,
        deps,
        prepared,
        parent_metadata,
        writer,
        persistence_lock,
        publish_direct,
        True,
    )


def _run_prepared_agent_call(
    state: dict[str, Any],
    deps: AppDependencies,
    prepared: _PreparedAgentCall,
    parent_metadata: dict[str, Any],
    writer: Any | None,
    persistence_lock: Lock | None = None,
    publish_direct: bool = True,
    emit_started: bool = True,
) -> dict[str, Any]:
    call = prepared.call
    request = prepared.request
    metadata = prepared.metadata
    child_state = prepared.child_state
    started_event = prepared.started_event

    def emit_stream_event(item: dict[str, Any]) -> None:
        if publish_direct:
            deps.run_event_stream_service.publish(state.get("thread_id"), item)
        if writer is not None:
            writer(item)

    if emit_started:
        emit_stream_event(started_event)
    child_writer = emit_stream_event if writer is not None or bool(parent_metadata.get("streaming_enabled")) else None
    child_result, child_events, forwarded_events = _run_child_graph(deps, child_state, request, state, metadata, child_writer)
    metadata, result, finished_event = _summarize_child_run(state, metadata, request, child_result)
    emit_stream_event(finished_event)
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
    next_parent_metadata = dict(parent_metadata)
    refs = list(parent_metadata.get("child_run_refs", []))
    if metadata.child_run_id not in refs:
        refs.append(metadata.child_run_id)
    next_parent_metadata["child_run_refs"] = refs
    persistence_events: list[dict[str, Any]] = []
    try:
        with _optional_lock(persistence_lock):
            deps.session_storage.append_tool_call(state["project_root"], state["session_id"], dump_model(tool_result))
    except Exception as exc:
        persistence_events.append(
            event(
                "subagent_event",
                session_id=state.get("session_id"),
                severity="warning",
                child_run_id=metadata.child_run_id,
                child_event_type="agent_tool_result_persistence_error",
                error_type=exc.__class__.__name__,
                message=str(exc),
            )
        )
    try:
        with _optional_lock(persistence_lock):
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
        "metadata": next_parent_metadata,
        "child_runs": [child_record],
        "pending_tool_calls": [],
        "tool_results": [dump_model(tool_result)],
        "messages": [tool_result_to_tool_message(tool_result)],
        "ui_events": [started_event, *forwarded_events, *persistence_events, finished_event],
    }


class _optional_lock:
    def __init__(self, lock: Lock | None) -> None:
        self.lock = lock

    def __enter__(self) -> None:
        if self.lock is not None:
            self.lock.acquire()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.lock is not None:
            self.lock.release()


def _run_child_graph(
    deps: AppDependencies,
    child_state: dict[str, Any],
    request: SubagentRequest,
    parent_state: dict[str, Any],
    metadata: ChildRunMetadata,
    writer: Any | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run the same compiled main graph for an isolated child state."""

    from langgraph_agent_blueprint.graph.builder import build_main_graph
    from langgraph_agent_blueprint.graph.checkpoints import default_checkpointer

    app = build_main_graph(deps).compile(checkpointer=default_checkpointer())
    config = {
        "configurable": {"thread_id": child_state["thread_id"]},
        "recursion_limit": max(12, request.max_turns * 8),
    }
    if writer is None:
        result = app.invoke(child_state, config)
        child_result = result if isinstance(result, dict) else {"final_response": str(result)}
        child_events = child_result.get("ui_events", []) if isinstance(child_result, dict) else []
        return child_result, child_events, [_forward_child_event(parent_state, metadata, item) for item in child_events]
    final_chunk: dict[str, Any] | None = None
    previous_count: int | None = None
    child_events: list[dict[str, Any]] = []
    forwarded_events: list[dict[str, Any]] = []
    for raw_chunk in app.stream(child_state, config, stream_mode=["custom", "values"]):
        mode, chunk = raw_chunk if isinstance(raw_chunk, tuple) and len(raw_chunk) == 2 else ("values", raw_chunk)
        if mode == "custom":
            if isinstance(chunk, dict) and "type" in chunk and "data" in chunk:
                child_events.append(chunk)
                forwarded = _forward_child_event(parent_state, metadata, chunk)
                forwarded_events.append(forwarded)
                writer(forwarded)
            continue
        if not isinstance(chunk, dict):
            continue
        final_chunk = chunk
        events = chunk.get("ui_events", [])
        if previous_count is None:
            previous_count = len(events)
            continue
        for item in events[previous_count:]:
            child_events.append(item)
            forwarded = _forward_child_event(parent_state, metadata, item)
            forwarded_events.append(forwarded)
            writer(forwarded)
        previous_count = len(events)
    return final_chunk or {}, child_events, forwarded_events


def _forward_child_event(parent_state: dict[str, Any], metadata: ChildRunMetadata, child_event: dict[str, Any]) -> dict[str, Any]:
    return event(
        "subagent_event",
        session_id=parent_state.get("session_id"),
        child_run_id=metadata.child_run_id,
        child_event_type=child_event.get("type"),
        child_event=child_event,
    )


def _stream_writer(state: dict[str, Any]) -> Any | None:
    if not state.get("metadata", {}).get("streaming_enabled"):
        return None
    try:
        return get_stream_writer()
    except RuntimeError:
        return None


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
