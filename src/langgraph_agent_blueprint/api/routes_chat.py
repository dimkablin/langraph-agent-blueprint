"""FastAPI chat streaming routes that expose graph events to HTTP clients."""

import json
from collections.abc import Iterable
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from langgraph_agent_blueprint.models.conversations import ConversationCreate, MessageCreate
from langgraph_agent_blueprint.services.conversation_service import ConversationAccessError, title_from_message

from .schemas import ApprovalRequest, ChatCancelRequest, ChatCancelResponse, ChatRequest, RuntimeEventDTO, StreamFrame
from .serializers import runtime_event_dto

router = APIRouter()


@router.post(
    "/chat/stream",
    responses={
        200: {
            "model": StreamFrame,
            "content": {"text/event-stream": {}},
            "description": "SSE stream of StreamFrame JSON payloads.",
        }
    },
)
def chat_stream(request_body: ChatRequest, request: Request, x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> StreamingResponse:
    """Stream one graph turn as browser-friendly Server-Sent Events."""

    runtime = request.app.state.runtime
    conversation_service = getattr(runtime.dependencies, "conversation_service", None)
    user_id = _user_id(x_user_id)
    conversation = None
    if conversation_service is not None:
        if request_body.session_id:
            try:
                conversation = conversation_service.get_conversation(user_id, request_body.session_id).conversation
            except ConversationAccessError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            conversation = conversation_service.create_conversation(
                user_id,
                ConversationCreate(title=title_from_message(request_body.message), project_id=request_body.project_id),
            )
    session_id = conversation.session_id if conversation is not None else request_body.session_id
    thread_id = (request_body.thread_id or conversation.thread_id) if conversation is not None else request_body.thread_id
    attachments = [item.model_dump(mode="json", exclude_none=True) for item in request_body.attachments]
    events = runtime.stream(
        request_body.message,
        input_kind="headless",
        project_id=request_body.project_id,
        session_id=session_id,
        thread_id=thread_id,
        model_intelligence=request_body.model_intelligence,
        permission_mode=request_body.permission_mode,
        attachments=attachments,
    )
    on_complete = None
    if conversation_service is not None and conversation is not None:
        on_complete = lambda final_response, captured_events: conversation_service.append_turn(
            user_id,
            conversation.conversation_id,
            user_message=MessageCreate(role="user", content=request_body.message),
            assistant_message=MessageCreate(role="assistant", content=final_response) if final_response is not None else None,
            events=captured_events,
        )
    return StreamingResponse(
        _sse_event_stream(
            events,
            redactor=runtime.dependencies.observability_service.redact_payload,
            on_complete=on_complete,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/cancel", response_model=ChatCancelResponse)
def chat_cancel(request_body: ChatCancelRequest, request: Request) -> ChatCancelResponse:
    """Request cooperative cancellation for the active graph run on a thread."""

    runtime = request.app.state.runtime
    result = runtime.cancel(
        request_body.thread_id,
        session_id=request_body.session_id,
        reason=request_body.reason,
    )
    payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
    return ChatCancelResponse.model_validate(payload)


@router.post("/approval/events", response_model=list[RuntimeEventDTO])
def approval_events(request_body: ApprovalRequest, request: Request) -> list[RuntimeEventDTO]:
    runtime = request.app.state.runtime
    result = runtime.resume(request_body.thread_id, request_body.decision_payload(), session_id=request_body.session_id)
    return [
        runtime_event_dto(item, redactor=runtime.dependencies.observability_service.redact_payload)
        for item in result.get("ui_events", [])
    ]


__all__ = ["router"]


def _sse_event_stream(events: Iterable[dict[str, Any]], *, redactor: Any, on_complete: Any | None = None) -> Iterable[str]:
    session_id: str | None = None
    final_response: str | None = None
    captured_events = []
    try:
        for event in events:
            dto = runtime_event_dto(event, redactor=redactor)
            captured_events.append(_stream_event_create_from_dto(dto))
            session_id = _session_id_from_event(dto, session_id)
            if dto.type == "final_response":
                final_response = str(dto.data.get("content") or "")
            yield _sse_frame("runtime_event", StreamFrame(type="event", event=dto).model_dump(mode="json", exclude_none=True))
        if on_complete is not None:
            on_complete(final_response, captured_events)
        yield _sse_frame("done", _done_frame_payload(session_id=session_id, final_response=final_response))
    except Exception as exc:
        yield _sse_frame("error", StreamFrame(type="error", error=str(exc)).model_dump(mode="json", exclude_none=True))


def _session_id_from_event(event: RuntimeEventDTO, current: str | None) -> str | None:
    if event.session_id and event.session_id != "unknown":
        return event.session_id
    data_session_id = event.data.get("session_id")
    return str(data_session_id) if data_session_id else current


def _done_frame_payload(*, session_id: str | None, final_response: str | None) -> dict[str, Any]:
    payload = StreamFrame(type="done", session_id=session_id, final_response=final_response).model_dump(
        mode="json",
        exclude_none=True,
    )
    payload["final_response"] = final_response
    return payload


def _sse_frame(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _stream_event_create_from_dto(event: RuntimeEventDTO):
    from langgraph_agent_blueprint.models.conversations import StreamEventCreate

    return StreamEventCreate(
        event_id=event.id,
        type=event.type,
        payload=event.data,
        metadata={"session_id": event.session_id, "node": event.node, "severity": event.severity, "timestamp": event.timestamp.isoformat()},
    )


def _user_id(header_value: str | None) -> str:
    user_id = (header_value or "dev-user").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header cannot be empty")
    if len(user_id) > 128:
        raise HTTPException(status_code=400, detail="X-User-Id header is too long")
    return user_id
