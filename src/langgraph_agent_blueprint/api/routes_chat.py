"""FastAPI chat streaming routes that expose graph events to HTTP clients."""

import json
from collections.abc import Iterable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

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
def chat_stream(request_body: ChatRequest, request: Request) -> StreamingResponse:
    """Stream one graph turn as browser-friendly Server-Sent Events."""

    runtime = request.app.state.runtime
    attachments = [item.model_dump(mode="json", exclude_none=True) for item in request_body.attachments]
    events = runtime.stream(
        request_body.message,
        input_kind="headless",
        project_id=request_body.project_id,
        session_id=request_body.session_id,
        thread_id=request_body.thread_id,
        model_intelligence=request_body.model_intelligence,
        attachments=attachments,
    )
    return StreamingResponse(
        _sse_event_stream(events, redactor=runtime.dependencies.observability_service.redact_payload),
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


def _sse_event_stream(events: Iterable[dict[str, Any]], *, redactor: Any) -> Iterable[str]:
    session_id: str | None = None
    final_response: str | None = None
    try:
        for event in events:
            dto = runtime_event_dto(event, redactor=redactor)
            session_id = _session_id_from_event(dto, session_id)
            if dto.type == "final_response":
                final_response = str(dto.data.get("content") or "")
            yield _sse_frame("runtime_event", StreamFrame(type="event", event=dto).model_dump(mode="json", exclude_none=True))
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
