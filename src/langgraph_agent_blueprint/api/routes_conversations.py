"""FastAPI routes for user-scoped durable conversation history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response

from langgraph_agent_blueprint.models.conversations import (
    ConversationCreate,
    ConversationDetail,
    ConversationListItem,
    ConversationRecord,
)
from langgraph_agent_blueprint.services.conversation_service import ConversationAccessError

from .schemas import ConversationAppendRequest, ConversationRenameRequest

router = APIRouter(prefix="/conversations", tags=["conversations"])

UserIdHeader = Annotated[str | None, Header(alias="X-User-Id")]


@router.post("", response_model=ConversationRecord)
def create_conversation(request_body: ConversationCreate, request: Request, x_user_id: UserIdHeader = None) -> ConversationRecord:
    """Create a new conversation owned by the current user."""

    return request.app.state.runtime.dependencies.conversation_service.create_conversation(_user_id(x_user_id), request_body)


@router.get("", response_model=list[ConversationListItem])
def list_conversations(
    request: Request,
    x_user_id: UserIdHeader = None,
    include_archived: bool = False,
    q: str | None = None,
    limit: int = 100,
) -> list[ConversationListItem]:
    """List or search conversations visible to the current user only."""

    service = request.app.state.runtime.dependencies.conversation_service
    user_id = _user_id(x_user_id)
    if q is not None:
        return service.search_conversations(user_id, q, include_archived=include_archived, limit=limit)
    return service.list_conversations(user_id, include_archived=include_archived, limit=limit)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, request: Request, x_user_id: UserIdHeader = None) -> ConversationDetail:
    """Return a full conversation snapshot if it belongs to the current user."""

    try:
        return request.app.state.runtime.dependencies.conversation_service.get_conversation(_user_id(x_user_id), conversation_id)
    except ConversationAccessError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{conversation_id}", response_model=ConversationRecord)
def rename_conversation(
    conversation_id: str,
    request_body: ConversationRenameRequest,
    request: Request,
    x_user_id: UserIdHeader = None,
) -> ConversationRecord:
    """Rename a user-owned conversation."""

    try:
        return request.app.state.runtime.dependencies.conversation_service.rename_conversation(
            _user_id(x_user_id),
            conversation_id,
            request_body.title,
        )
    except ConversationAccessError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{conversation_id}/archive", response_model=ConversationRecord)
def archive_conversation(conversation_id: str, request: Request, x_user_id: UserIdHeader = None) -> ConversationRecord:
    """Archive a user-owned conversation so it is hidden from normal history lists."""

    try:
        return request.app.state.runtime.dependencies.conversation_service.archive_conversation(_user_id(x_user_id), conversation_id)
    except ConversationAccessError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, request: Request, x_user_id: UserIdHeader = None) -> Response:
    """Soft-delete a user-owned conversation."""

    try:
        request.app.state.runtime.dependencies.conversation_service.soft_delete_conversation(_user_id(x_user_id), conversation_id)
    except ConversationAccessError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
def append_conversation_messages(
    conversation_id: str,
    request_body: ConversationAppendRequest,
    request: Request,
    x_user_id: UserIdHeader = None,
) -> ConversationDetail:
    """Append one idempotent turn/messages/events batch to a user-owned conversation."""

    try:
        return request.app.state.runtime.dependencies.conversation_service.append_turn(
            _user_id(x_user_id),
            conversation_id,
            user_message=request_body.user_message,
            assistant_message=request_body.assistant_message,
            events=request_body.events,
            tool_calls=request_body.tool_calls,
            artifacts=request_body.artifacts,
        )
    except ConversationAccessError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _user_id(header_value: str | None) -> str:
    """Resolve the API user id from the authenticated/dev-mode request boundary."""

    user_id = (header_value or "dev-user").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header cannot be empty")
    if len(user_id) > 128:
        raise HTTPException(status_code=400, detail="X-User-Id header is too long")
    return user_id


__all__ = ["router"]
