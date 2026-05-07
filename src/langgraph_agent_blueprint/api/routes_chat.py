"""FastAPI chat streaming routes that expose graph events to HTTP clients."""

from fastapi import APIRouter, Request

from .schemas import ApprovalRequest, ChatRequest

router = APIRouter()


@router.post("/chat/stream")
def chat_stream(request_body: ChatRequest, request: Request) -> list[dict]:
    runtime = request.app.state.runtime
    attachments = [item.model_dump(mode="json", exclude_none=True) for item in request_body.attachments]
    return list(
        runtime.stream(
            request_body.message,
            input_kind="headless",
            session_id=request_body.session_id,
            thread_id=request_body.thread_id,
            attachments=attachments,
        )
    )


@router.post("/approval/events")
def approval_events(request_body: ApprovalRequest, request: Request) -> list[dict]:
    runtime = request.app.state.runtime
    result = runtime.resume(request_body.thread_id, request_body.decision, session_id=request_body.session_id)
    return result.get("ui_events", [])


__all__ = ["router"]
