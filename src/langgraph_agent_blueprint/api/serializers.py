"""Frontend-facing API serialization helpers.

These helpers keep FastAPI route handlers thin and prevent frontend endpoints
from exposing raw session-storage or LangChain object shapes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage

from langgraph_agent_blueprint.models import RuntimeEvent
from langgraph_agent_blueprint.utils.serialization import message_to_dict

from .schemas import (
    ChildRunDetailDTO,
    ChildRunListItemDTO,
    ContextStateDTO,
    MessageDTO,
    RuntimeEventDTO,
    SessionDetailDTO,
    SessionListItemDTO,
    ToolCallRecordDTO,
)


MAX_FRONTEND_TEXT_CHARS = 20_000


def runtime_event_dto(event: dict[str, Any] | RuntimeEvent, *, redactor: Any | None = None) -> RuntimeEventDTO:
    """Validate and redact one RuntimeEvent for frontend delivery."""

    payload = event.model_dump(mode="json") if isinstance(event, RuntimeEvent) else dict(event)
    dto = RuntimeEventDTO.model_validate(payload)
    if redactor is None:
        return dto
    return dto.model_copy(update={"data": _frontend_event_data(dto.type, dto.data, redactor=redactor)})


def runtime_event_dtos(events: list[dict[str, Any]], *, redactor: Any | None = None) -> list[RuntimeEventDTO]:
    """Validate and redact RuntimeEvent records, dropping corrupt rows at the API edge."""

    items: list[RuntimeEventDTO] = []
    for event in events:
        try:
            items.append(runtime_event_dto(event, redactor=redactor))
        except (TypeError, ValueError):
            continue
    return items


def session_event_dtos(snapshot: dict[str, Any], *, redactor: Any | None = None) -> list[RuntimeEventDTO]:
    """Return persisted session events plus a final-response event when storage predates finalization."""

    events = runtime_event_dtos(snapshot.get("events", []) or [], redactor=redactor)
    if any(item.type == "final_response" for item in events):
        return events
    final_response = _last_ai_message_content(snapshot.get("messages", []) or [])
    if not final_response:
        return events
    metadata = snapshot.get("metadata", {}) if isinstance(snapshot.get("metadata"), dict) else {}
    payload = {
        "id": f"{metadata.get('session_id') or 'session'}-final-response",
        "type": "final_response",
        "timestamp": metadata.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        "session_id": metadata.get("session_id") or "unknown",
        "severity": "info",
        "data": {"content": _bounded_text(final_response)},
    }
    if redactor is not None:
        payload = redactor(payload)
    return [*events, RuntimeEventDTO.model_validate(payload)]


def message_dtos(messages: list[Any]) -> list[MessageDTO]:
    """Normalize LangChain or persisted message objects into frontend DTOs."""

    normalized: list[MessageDTO] = []
    for index, message in enumerate(messages):
        payload = _message_payload(message)
        if _is_internal_compaction_message(payload):
            continue
        normalized.append(
            MessageDTO(
                id=str(payload.get("id") or f"message-{index}"),
                role=str(payload.get("role") or "unknown"),
                type=payload.get("type"),
                content=_bounded_text(payload.get("content", "")),
                tool_calls=payload.get("tool_calls") if isinstance(payload.get("tool_calls"), list) else [],
                tool_call_id=payload.get("tool_call_id"),
            )
        )
    return normalized


def tool_call_dtos(records: list[dict[str, Any]], *, redactor: Any | None = None) -> list[ToolCallRecordDTO]:
    """Normalize stored tool-result records for frontend display."""

    items: list[ToolCallRecordDTO] = []
    for record in records:
        payload = redactor(record) if redactor is not None else record
        items.append(
            ToolCallRecordDTO(
                id=str(payload.get("id") or payload.get("tool_call_id") or ""),
                name=str(payload.get("name") or payload.get("tool_name") or ""),
                status=str(payload.get("status") or "unknown"),
                content=_bounded_text(payload.get("content", "")),
                output_ref=payload.get("output_ref"),
                metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
                error=payload.get("error"),
            )
        )
    return items


def context_state_dto(snapshot: dict[str, Any], *, redactor: Any | None = None) -> ContextStateDTO:
    """Extract context side-panel state from a persisted session snapshot."""

    metadata = snapshot.get("metadata", {}) if isinstance(snapshot.get("metadata"), dict) else {}
    context_status = metadata.get("context_status") if isinstance(metadata.get("context_status"), dict) else {}
    context = ContextStateDTO(
        references=_as_list(metadata.get("context_references")),
        fragments=_as_list(metadata.get("resolved_context") or context_status.get("context_fragments")),
        attachments=_as_list(metadata.get("attachments")),
        budget=metadata.get("context_budget") if isinstance(metadata.get("context_budget"), dict) else {},
        errors=_as_list(metadata.get("context_errors") or context_status.get("context_errors")),
    )
    if redactor is None:
        return context
    return ContextStateDTO.model_validate(redactor(context.model_dump(mode="json")))


def session_list_item_dto(
    metadata: dict[str, Any],
    snapshot: dict[str, Any] | None = None,
    *,
    child_run_count: int = 0,
) -> SessionListItemDTO:
    """Build one frontend session-list row from metadata plus optional loaded counts."""

    snapshot = snapshot or {}
    messages = snapshot.get("messages", []) or []
    return SessionListItemDTO(
        session_id=str(metadata.get("session_id") or ""),
        title=_session_title(metadata, messages),
        created_at=metadata.get("created_at"),
        updated_at=metadata.get("updated_at"),
        provider=metadata.get("provider"),
        model=metadata.get("model"),
        message_count=len(message_dtos(messages)),
        event_count=len(snapshot.get("events", []) or []),
        tool_call_count=len(snapshot.get("tool_calls", []) or []),
        child_run_count=child_run_count,
        usage=snapshot.get("usage") if isinstance(snapshot.get("usage"), dict) else metadata.get("usage", {}),
    )


def session_detail_dto(
    snapshot: dict[str, Any],
    *,
    child_runs: list[ChildRunListItemDTO] | None = None,
    redactor: Any | None = None,
) -> SessionDetailDTO:
    """Build a frontend-safe session detail DTO without raw storage-only fields."""

    metadata = snapshot.get("metadata", {}) if isinstance(snapshot.get("metadata"), dict) else {}
    messages = snapshot.get("messages", []) or []
    safe_metadata = {
        key: value
        for key, value in metadata.items()
        if key not in {"project_root", "cwd", "config", "config_report"}
    }
    if redactor is not None:
        safe_metadata = redactor(safe_metadata)
    return SessionDetailDTO(
        session_id=str(metadata.get("session_id") or ""),
        title=_session_title(metadata, messages),
        created_at=metadata.get("created_at"),
        updated_at=metadata.get("updated_at"),
        provider=metadata.get("provider"),
        model=metadata.get("model"),
        messages=message_dtos(messages),
        events=session_event_dtos(snapshot, redactor=redactor),
        tool_calls=tool_call_dtos(snapshot.get("tool_calls", []) or [], redactor=redactor),
        todos=snapshot.get("todos", []) or [],
        memory=snapshot.get("memory", {}) or {},
        usage=snapshot.get("usage", {}) or {},
        context=context_state_dto(snapshot, redactor=redactor),
        child_runs=child_runs or [],
        metadata=safe_metadata,
    )


def child_run_list_item_dto(raw: dict[str, Any], result: dict[str, Any] | None = None) -> ChildRunListItemDTO:
    """Build a child-run list row from stored metadata/result files."""

    result = result or {}
    return ChildRunListItemDTO(
        child_run_id=str(raw.get("child_run_id") or ""),
        parent_session_id=raw.get("parent_session_id"),
        child_session_id=raw.get("child_session_id"),
        child_thread_id=raw.get("child_thread_id"),
        name=raw.get("name"),
        purpose=raw.get("purpose"),
        status=raw.get("status"),
        started_at=raw.get("started_at"),
        completed_at=raw.get("completed_at"),
        summary=result.get("summary"),
    )


def child_run_detail_dto(raw: dict[str, Any], *, redactor: Any | None = None) -> ChildRunDetailDTO:
    """Build child-run detail DTO from storage records."""

    metadata = raw.get("metadata", {}) if isinstance(raw.get("metadata"), dict) else {}
    result = raw.get("result", {}) if isinstance(raw.get("result"), dict) else {}
    if redactor is not None:
        metadata = redactor(metadata)
        result = redactor(result)
    return ChildRunDetailDTO(
        metadata=metadata,
        result=result,
        events=runtime_event_dtos(raw.get("events", []) or [], redactor=redactor),
    )


def export_path_for_frontend(path: Path, root: Path) -> str:
    """Return a storage-relative export path when possible, falling back to basename."""

    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name


def _frontend_event_data(event_type: str, data: dict[str, Any], *, redactor: Any) -> dict[str, Any]:
    """Redact event payloads without allowing observability truncation to replace the event envelope."""

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        key_text = str(key)
        if (key_text == "content" and event_type in {"model_message", "final_response"}) or (
            key_text == "token" and event_type == "model_token"
        ):
            redacted[key_text] = _bounded_text(value)
            continue
        scoped = redactor({key_text: value})
        if isinstance(scoped, dict) and key_text in scoped:
            redacted[key_text] = scoped[key_text]
        else:
            redacted[key_text] = scoped
    return redacted


def _message_payload(message: Any) -> dict[str, Any]:
    if isinstance(message, BaseMessage):
        return message_to_dict(message)
    if isinstance(message, dict):
        return dict(message)
    return {"role": "unknown", "content": str(message), "type": type(message).__name__}


def _last_ai_message_content(messages: list[Any]) -> str | None:
    for message in reversed(messages):
        payload = _message_payload(message)
        if payload.get("role") == "ai" and payload.get("content"):
            return _bounded_text(payload["content"])
    return None


def _session_title(metadata: dict[str, Any], messages: list[Any]) -> str | None:
    stored_title = str(metadata.get("title") or "")[:72]
    if stored_title:
        return stored_title
    return _first_chat_message_title(messages)


def _first_chat_message_title(messages: list[Any]) -> str | None:
    fallback: str | None = None
    for message in messages:
        payload = _message_payload(message)
        if _is_internal_compaction_message(payload):
            continue
        content = _bounded_text(payload.get("content", ""))[:72]
        if not content:
            continue
        role = payload.get("role")
        if role in {"human", "user"}:
            return content
        if fallback is None:
            fallback = content
    return fallback


def _bounded_text(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            text = str(value)
    if len(text) <= MAX_FRONTEND_TEXT_CHARS:
        return text
    return text[:MAX_FRONTEND_TEXT_CHARS] + "...<truncated>"


def _is_internal_compaction_message(payload: dict[str, Any]) -> bool:
    return str(payload.get("role") or "") == "system" and str(payload.get("content") or "").startswith("Compacted prior context:")


def _as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
