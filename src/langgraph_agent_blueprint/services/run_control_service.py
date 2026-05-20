"""In-memory runtime control for stopping active graph runs."""

from __future__ import annotations

from threading import Lock

from langgraph_agent_blueprint.models import RunCancellationResult
from langgraph_agent_blueprint.utils.ids import validate_session_id, validate_thread_id


DEFAULT_CANCELLATION_REASON = "Generation stopped by user."


class RunControlService:
    """Track active graph runs and cooperative cancellation requests by thread id."""

    def __init__(self) -> None:
        self._active_sessions: dict[str, str | None] = {}
        self._cancelled_reasons: dict[str, str] = {}
        self._lock = Lock()

    def start_run(self, thread_id: str, *, session_id: str | None = None) -> None:
        thread_id = validate_thread_id(thread_id)
        session_id = validate_session_id(session_id) if session_id is not None else None
        with self._lock:
            self._active_sessions[thread_id] = session_id
            self._cancelled_reasons.pop(thread_id, None)

    def finish_run(self, thread_id: str) -> None:
        thread_id = validate_thread_id(thread_id)
        with self._lock:
            self._active_sessions.pop(thread_id, None)
            self._cancelled_reasons.pop(thread_id, None)

    def cancel(
        self,
        thread_id: str,
        *,
        session_id: str | None = None,
        reason: str | None = None,
    ) -> RunCancellationResult:
        thread_id = validate_thread_id(thread_id)
        session_id = validate_session_id(session_id) if session_id is not None else None
        cancellation_reason = (reason or DEFAULT_CANCELLATION_REASON).strip() or DEFAULT_CANCELLATION_REASON
        with self._lock:
            is_active = thread_id in self._active_sessions
            if is_active:
                self._cancelled_reasons[thread_id] = cancellation_reason
        return RunCancellationResult(
            cancelled=is_active,
            thread_id=thread_id,
            session_id=session_id,
            reason=cancellation_reason,
        )

    def is_cancelled(self, thread_id: str | None) -> bool:
        if not thread_id:
            return False
        with self._lock:
            return thread_id in self._cancelled_reasons

    def cancellation_reason(self, thread_id: str | None) -> str:
        if not thread_id:
            return DEFAULT_CANCELLATION_REASON
        with self._lock:
            return self._cancelled_reasons.get(thread_id, DEFAULT_CANCELLATION_REASON)
