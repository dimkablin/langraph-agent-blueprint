"""In-process event bridge for graph-node progress that must stream before node completion."""

from __future__ import annotations

from queue import Queue
from threading import Lock
from typing import Any


class RunEventStreamService:
    """Publish runtime events to an active HTTP/SSE stream by thread id."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._queues: dict[str, Queue[dict[str, Any]]] = {}

    def attach(self, thread_id: str | None, queue: Queue[dict[str, Any]]) -> None:
        if not thread_id:
            return
        with self._lock:
            self._queues[str(thread_id)] = queue

    def detach(self, thread_id: str | None) -> None:
        if not thread_id:
            return
        with self._lock:
            self._queues.pop(str(thread_id), None)

    def publish(self, thread_id: str | None, event: dict[str, Any]) -> bool:
        if not thread_id:
            return False
        with self._lock:
            queue = self._queues.get(str(thread_id))
        if queue is None:
            return False
        queue.put(event)
        return True
