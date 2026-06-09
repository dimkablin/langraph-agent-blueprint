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
from langgraph.types import Command

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.state import AssistantState
from langgraph_agent_blueprint.models import (
    AgentActivityEvent,
    AgentActivitySource,
    ChildRunMetadata,
    PermissionDecision,
    PermissionRequest,
    PermissionStateStreamEvent,
    SubagentRequest,
    SubagentResult,
    ToolCall,
    ToolResult,
    dump_model,
    event,
    stream_event_payload,
    tool_result_to_tool_message,
    validate_list,
)
from langgraph_agent_blueprint.tools import AgentInput
from langgraph_agent_blueprint.utils.activity import safe_activity_data


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
        if update.get("pending_subagent_approval"):
            return update
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
    pending_update: dict[str, Any] | None = None
    for update in ordered_results:
        if update.get("pending_subagent_approval") and pending_update is None:
            pending_update = update
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
    if pending_update is not None:
        next_update = dict(pending_update)
        next_update["ui_events"] = [*streamed_events, *non_streamed_events]
        return next_update
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
    if _child_interrupted(child_result):
        return _subagent_permission_update(
            state,
            deps,
            call,
            request,
            metadata,
            child_state,
            child_result,
            child_events,
            forwarded_events,
            parent_metadata,
            started_event,
            emit_stream_event,
        )
    return _finalize_prepared_agent_call(
        state,
        deps,
        call,
        request,
        metadata,
        parent_metadata,
        child_result,
        child_events,
        forwarded_events,
        started_event,
        persistence_lock=persistence_lock,
        emit_stream_event=emit_stream_event,
    )


def _finalize_prepared_agent_call(
    state: dict[str, Any],
    deps: AppDependencies,
    call: ToolCall,
    request: SubagentRequest,
    metadata: ChildRunMetadata,
    parent_metadata: dict[str, Any],
    child_result: dict[str, Any],
    child_events: list[dict[str, Any]],
    forwarded_events: list[dict[str, Any]],
    started_event: dict[str, Any] | None,
    *,
    persistence_lock: Lock | None = None,
    emit_stream_event: Any | None = None,
) -> dict[str, Any]:
    metadata, result, finished_event = _summarize_child_run(state, metadata, request, child_result)
    if emit_stream_event is not None:
        emit_stream_event(finished_event)
    if metadata.status != "running":
        deps.agent_service.delete_child_thread(deps.config.storage_dir, metadata.child_thread_id)
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
    next_parent_metadata.pop("agent_route", None)
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
        "pending_subagent_approval": None,
        "pending_tool_calls": [],
        "tool_results": [dump_model(tool_result)],
        "messages": [tool_result_to_tool_message(tool_result)],
        "ui_events": [*([started_event] if started_event is not None else []), *forwarded_events, *persistence_events, finished_event],
    }


def resume_pending_subagent_approval(state: dict[str, Any], deps: AppDependencies, decision_payload: object) -> dict[str, Any]:
    """Resume the child graph represented by ``pending_subagent_approval``."""

    pending = state.get("pending_subagent_approval")
    if not isinstance(pending, dict):
        return {}
    request = PermissionRequest.model_validate(pending.get("permission_request", {}))
    decision = _resume_permission_decision(request, decision_payload)
    record = _permission_decision_record(request, decision)
    resolution_event = _subagent_permission_resolved_event(state, request, record)
    call = ToolCall.model_validate(pending.get("agent_call", {}))
    subagent_request = SubagentRequest.model_validate(pending.get("request", {}))
    metadata = ChildRunMetadata.model_validate(pending.get("metadata", {}))
    parent_metadata = dict(pending.get("parent_metadata", state.get("metadata", {})))
    child_events_before = list(pending.get("child_events", [])) if isinstance(pending.get("child_events"), list) else []

    if decision.decision == "rejected":
        child_resolution_event = _child_permission_resolved_event(metadata, request, record)
        child_events = [*child_events_before, child_resolution_event]
        forwarded_events = [_forward_child_event(state, metadata, child_resolution_event)]
        child_result = _rejected_child_result(pending, request, decision)
        update = _finalize_prepared_agent_call(
            state,
            deps,
            call,
            subagent_request,
            metadata,
            parent_metadata,
            child_result,
            child_events,
            forwarded_events,
            None,
        )
        return {**update, "ui_events": [resolution_event, *update.get("ui_events", [])]}

    child_result, new_child_events, new_forwarded_events = _resume_child_graph(
        deps,
        pending,
        decision.model_dump(mode="json", exclude_none=True),
        state,
        metadata,
        None,
    )
    child_events = [*child_events_before, *new_child_events]
    if _child_interrupted(child_result):
        update = _subagent_permission_update(
            state,
            deps,
            call,
            subagent_request,
            metadata,
            pending.get("child_state", {}),
            child_result,
            child_events,
            new_forwarded_events,
            parent_metadata,
            None,
            None,
        )
        return {**update, "ui_events": [resolution_event, *update.get("ui_events", [])]}
    update = _finalize_prepared_agent_call(
        state,
        deps,
        call,
        subagent_request,
        metadata,
        parent_metadata,
        child_result,
        child_events,
        new_forwarded_events,
        None,
    )
    return {**update, "ui_events": [resolution_event, *update.get("ui_events", [])]}


def _subagent_permission_update(
    state: dict[str, Any],
    deps: AppDependencies,
    call: ToolCall,
    request: SubagentRequest,
    metadata: ChildRunMetadata,
    child_state: dict[str, Any],
    child_result: dict[str, Any],
    child_events: list[dict[str, Any]],
    forwarded_events: list[dict[str, Any]],
    parent_metadata: dict[str, Any],
    started_event: dict[str, Any] | None,
    emit_stream_event: Any | None,
) -> dict[str, Any]:
    permission_request = _subagent_permission_request(child_result, metadata)
    permission_event = _subagent_permission_required_event(state, permission_request)
    if emit_stream_event is not None:
        emit_stream_event(permission_event)
    next_parent_metadata = dict(parent_metadata)
    next_parent_metadata["agent_route"] = "needs_subagent_permission"
    pending = {
        "agent_call": dump_model(call),
        "request": dump_model(request),
        "metadata": dump_model(metadata),
        "child_state": child_state,
        "child_events": child_events,
        "parent_metadata": next_parent_metadata,
        "permission_request": permission_request,
    }
    return {
        "metadata": next_parent_metadata,
        "pending_subagent_approval": pending,
        "ui_events": [*([started_event] if started_event is not None else []), *forwarded_events, permission_event],
    }


def _child_interrupted(child_result: dict[str, Any]) -> bool:
    return bool(child_result.get("__interrupt__"))


def _subagent_permission_request(child_result: dict[str, Any], metadata: ChildRunMetadata) -> dict[str, Any]:
    payload = _interrupt_value(child_result)
    if not payload:
        payload = child_result.get("pending_confirmation", {}) if isinstance(child_result.get("pending_confirmation"), dict) else {}
    payload = dict(payload)
    payload.update(
        {
            "scope": "subagent",
            "parent_session_id": metadata.parent_session_id,
            "parent_thread_id": metadata.parent_thread_id,
            "child_session_id": metadata.child_session_id,
            "child_thread_id": metadata.child_thread_id,
            "child_run_id": metadata.child_run_id,
            "subagent_name": metadata.name,
        }
    )
    return dump_model(PermissionRequest.model_validate(payload))


def _interrupt_value(child_result: dict[str, Any]) -> dict[str, Any]:
    interrupts = child_result.get("__interrupt__")
    if not isinstance(interrupts, list) or not interrupts:
        return {}
    first = interrupts[0]
    value = getattr(first, "value", None)
    if isinstance(value, dict):
        return value
    if isinstance(first, dict):
        nested = first.get("value")
        return nested if isinstance(nested, dict) else first
    return {}


def _subagent_permission_required_event(parent_state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    request = PermissionRequest.model_validate(payload)
    return event(
        "permission_required",
        session_id=parent_state.get("session_id"),
        **payload,
        stream_event=stream_event_payload(_permission_state_stream_event(request, status="required")),
        activity=_subagent_permission_activity(request, status="pending", title="Subagent permission required").model_dump(mode="json"),
    )


def _subagent_permission_resolved_event(parent_state: dict[str, Any], request: PermissionRequest, record: dict[str, Any]) -> dict[str, Any]:
    status = "approved" if record["approved"] else "rejected"
    return event(
        "permission_resolved",
        session_id=parent_state.get("session_id"),
        **record,
        scope=request.scope,
        parent_session_id=request.parent_session_id,
        parent_thread_id=request.parent_thread_id,
        child_session_id=request.child_session_id,
        child_thread_id=request.child_thread_id,
        child_run_id=request.child_run_id,
        subagent_name=request.subagent_name,
        stream_event=stream_event_payload(_permission_state_stream_event(request, status=status, record=record)),
        activity=_subagent_permission_activity(
            request,
            status="success" if record["approved"] else "blocked",
            title="Subagent permission approved" if record["approved"] else "Subagent permission rejected",
            decision=record.get("decision"),
            reason=record.get("reason"),
        ).model_dump(mode="json"),
    )


def _child_permission_resolved_event(metadata: ChildRunMetadata, request: PermissionRequest, record: dict[str, Any]) -> dict[str, Any]:
    return event(
        "permission_resolved",
        session_id=metadata.child_session_id,
        **record,
        stream_event=stream_event_payload(_permission_state_stream_event(request, status="rejected", record=record)),
    )


def _permission_state_stream_event(
    request: PermissionRequest,
    *,
    status: str,
    record: dict[str, Any] | None = None,
) -> PermissionStateStreamEvent:
    reason = (record or {}).get("reason") or request.reason
    return PermissionStateStreamEvent(
        status=status,  # type: ignore[arg-type]
        tool_call_id=request.tool_call_id,
        tool_name=request.tool_name,
        action=request.action,
        risk=request.risk,
        args_summary=request.args_summary,
        reason=str(reason) if reason else None,
        args=request.args or {},
        scope=request.scope,
        parent_session_id=request.parent_session_id,
        parent_thread_id=request.parent_thread_id,
        child_session_id=request.child_session_id,
        child_thread_id=request.child_thread_id,
        child_run_id=request.child_run_id,
        subagent_name=request.subagent_name,
    )


def _subagent_permission_activity(
    request: PermissionRequest,
    *,
    status: str,
    title: str,
    decision: str | None = None,
    reason: str | None = None,
) -> AgentActivityEvent:
    summary = reason or request.reason or request.args_summary
    return AgentActivityEvent(
        id=f"activity_{request.child_run_id or request.tool_call_id}_{request.tool_call_id}_{status}",
        type="permission.subagent",
        source=AgentActivitySource(kind="permission", name=request.tool_name, component="AgentService"),
        category="permission",
        status=status,  # type: ignore[arg-type]
        title=title,
        summary=summary,
        data=safe_activity_data(
            {
                "tool_call_id": request.tool_call_id,
                "tool_name": request.tool_name,
                "action": request.action,
                "risk": request.risk,
                "args_summary": request.args_summary,
                "reason": summary,
                "decision": decision,
                "scope": request.scope,
                "child_run_id": request.child_run_id,
                "child_session_id": request.child_session_id,
                "child_thread_id": request.child_thread_id,
                "subagent_name": request.subagent_name,
            }
        ),
    )


def _resume_permission_decision(request: PermissionRequest, decision: object) -> PermissionDecision:
    if isinstance(decision, dict) and "decision" in decision:
        return PermissionDecision.model_validate({"tool_call_id": request.tool_call_id, **decision})
    if isinstance(decision, dict):
        approved = bool(decision.get("approved"))
        return PermissionDecision(
            tool_call_id=request.tool_call_id,
            decision="approved" if approved else "rejected",
            reason=decision.get("reason"),
            remember=bool(decision.get("remember", False)),
        )
    return PermissionDecision(tool_call_id=request.tool_call_id, decision="approved" if bool(decision) else "rejected")


def _permission_decision_record(request: PermissionRequest, decision: PermissionDecision) -> dict[str, Any]:
    approved = decision.decision == "approved"
    return {
        "tool_call_id": request.tool_call_id,
        "tool_name": request.tool_name,
        "approved": approved,
        "decision": decision.decision,
        "reason": decision.reason,
        "remember": decision.remember,
    }


def _rejected_child_result(pending: dict[str, Any], request: PermissionRequest, decision: PermissionDecision) -> dict[str, Any]:
    child_state = pending.get("child_state", {}) if isinstance(pending.get("child_state"), dict) else {}
    child_metadata = child_state.get("metadata", {}) if isinstance(child_state.get("metadata"), dict) else {}
    summary = f"Subagent tool call '{request.tool_name}' was rejected by user. No child side effect was executed."
    return {
        "final_response": summary,
        "errors": [{"type": "SubagentPermissionRejected", "message": summary, "reason": decision.reason}],
        "metadata": {"allowed_tools_override": child_metadata.get("allowed_tools_override", [])},
        "tool_results": [],
        "artifacts": [],
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

    app = build_main_graph(deps).compile(checkpointer=deps.agent_service.child_checkpointer(deps.config.storage_dir))
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


def _resume_child_graph(
    deps: AppDependencies,
    pending: dict[str, Any],
    decision: dict[str, Any],
    parent_state: dict[str, Any],
    metadata: ChildRunMetadata,
    writer: Any | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Resume an interrupted child graph and return only child events added after the pending approval."""

    from langgraph_agent_blueprint.graph.builder import build_main_graph

    request = SubagentRequest.model_validate(pending.get("request", {}))
    previous_events = list(pending.get("child_events", [])) if isinstance(pending.get("child_events"), list) else []
    previous_count = len(previous_events)
    app = build_main_graph(deps).compile(checkpointer=deps.agent_service.child_checkpointer(deps.config.storage_dir))
    config = {
        "configurable": {"thread_id": metadata.child_thread_id},
        "recursion_limit": max(12, request.max_turns * 8),
    }
    if writer is None:
        result = app.invoke(Command(resume=decision), config)
        child_result = result if isinstance(result, dict) else {"final_response": str(result)}
        events = child_result.get("ui_events", []) if isinstance(child_result, dict) else []
        child_events = events[previous_count:]
        return child_result, child_events, [_forward_child_event(parent_state, metadata, item) for item in child_events]
    final_chunk: dict[str, Any] | None = None
    child_events: list[dict[str, Any]] = []
    forwarded_events: list[dict[str, Any]] = []
    for raw_chunk in app.stream(Command(resume=decision), config, stream_mode=["custom", "values"]):
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
