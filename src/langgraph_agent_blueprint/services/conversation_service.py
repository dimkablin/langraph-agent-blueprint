"""User-scoped conversation history service."""

from __future__ import annotations

from typing import Any

from langgraph_agent_blueprint.models.conversations import (
    ArtifactCreate,
    ConversationCreate,
    ConversationDetail,
    ConversationListItem,
    ConversationRecord,
    MessageCreate,
    StreamEventCreate,
    ToolCallCreate,
)
from langgraph_agent_blueprint.storage.conversation_storage import ConversationNotFoundError, SQLiteConversationStorage


class ConversationAccessError(PermissionError):
    """Raised when a conversation is missing, deleted, or not owned by the requesting user."""


class ConversationService:
    """High-level use cases for durable multi-user chat history.

    Every public method takes user_id first so ownership checks happen in the service layer
    instead of relying on frontend filtering.
    """

    def __init__(self, storage: SQLiteConversationStorage) -> None:
        self.storage = storage

    def create_conversation(self, user_id: str, request: ConversationCreate) -> ConversationRecord:
        return self.storage.create_conversation(self._user_id(user_id), request)

    def list_conversations(self, user_id: str, *, include_archived: bool = False, limit: int = 100) -> list[ConversationListItem]:
        return self.storage.list_conversations(self._user_id(user_id), include_archived=include_archived, limit=limit)

    def search_conversations(self, user_id: str, query: str, *, include_archived: bool = False, limit: int = 50) -> list[ConversationListItem]:
        if not query.strip():
            return []
        return self.storage.search_conversations(self._user_id(user_id), query, include_archived=include_archived, limit=limit)

    def get_conversation(self, user_id: str, conversation_id: str) -> ConversationDetail:
        try:
            return self.storage.get_conversation(self._user_id(user_id), conversation_id)
        except ConversationNotFoundError as exc:
            raise ConversationAccessError(f"Conversation not found: {conversation_id}") from exc

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> ConversationRecord:
        try:
            return self.storage.rename_conversation(self._user_id(user_id), conversation_id, title)
        except ConversationNotFoundError as exc:
            raise ConversationAccessError(f"Conversation not found: {conversation_id}") from exc

    def archive_conversation(self, user_id: str, conversation_id: str) -> ConversationRecord:
        try:
            return self.storage.archive_conversation(self._user_id(user_id), conversation_id)
        except ConversationNotFoundError as exc:
            raise ConversationAccessError(f"Conversation not found: {conversation_id}") from exc

    def soft_delete_conversation(self, user_id: str, conversation_id: str) -> None:
        try:
            self.storage.soft_delete_conversation(self._user_id(user_id), conversation_id)
        except ConversationNotFoundError as exc:
            raise ConversationAccessError(f"Conversation not found: {conversation_id}") from exc

    def append_turn(
        self,
        user_id: str,
        conversation_id: str,
        *,
        user_message: MessageCreate | None = None,
        assistant_message: MessageCreate | None = None,
        events: list[StreamEventCreate] | None = None,
        tool_calls: list[ToolCallCreate] | None = None,
        artifacts: list[ArtifactCreate] | None = None,
    ) -> ConversationDetail:
        try:
            return self.storage.append_turn(
                self._user_id(user_id),
                conversation_id,
                user_message=user_message,
                assistant_message=assistant_message,
                events=events,
                tool_calls=tool_calls,
                artifacts=artifacts,
            )
        except ConversationNotFoundError as exc:
            raise ConversationAccessError(f"Conversation not found: {conversation_id}") from exc

    @staticmethod
    def _user_id(user_id: str) -> str:
        clean = user_id.strip()
        if not clean:
            raise ValueError("user_id is required")
        if len(clean) > 128:
            raise ValueError("user_id is too long")
        return clean


def title_from_message(message: str) -> str:
    """Derive a bounded first-chat title without involving the LLM."""

    collapsed = " ".join(message.strip().split())
    return collapsed[:80] or "New chat"


def event_creates_from_runtime(events: list[dict[str, Any]] | None) -> list[StreamEventCreate]:
    """Map runtime event dicts to normalized durable event creates."""

    records: list[StreamEventCreate] = []
    for item in events or []:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("type") or "runtime")
        event_id = str(item.get("id")) if item.get("id") is not None else None
        payload = item.get("data") if isinstance(item.get("data"), dict) else {"raw": item}
        metadata = {key: value for key, value in item.items() if key not in {"id", "type", "data"}}
        records.append(StreamEventCreate(event_id=event_id, type=event_type, payload=payload, metadata=metadata))
    return records
