from fastapi import APIRouter, Request

from .schemas import ApprovalRequest, ChatRequest

router = APIRouter()


@router.post("/chat/stream")
def chat_stream(request_body: ChatRequest, request: Request) -> list[dict]:
    runtime = request.app.state.runtime
    return list(runtime.stream(request_body.message, input_kind="headless"))


@router.post("/approval/events")
def approval_events(request_body: ApprovalRequest, request: Request) -> list[dict]:
    runtime = request.app.state.runtime
    result = runtime.resume(request_body.thread_id, request_body.decision)
    return result.get("ui_events", [])


__all__ = ["router"]
