"""Measure persistence and memory-cache paths for the Hermes-inspired slice.

This script is intentionally small and dependency-light so QA can rerun the same
command on another checkout:

    python scripts/measure_persistence_performance.py

The numbers are wall-clock timings for local filesystem operations; compare the
shape of the measurements rather than treating one run as a universal benchmark.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from langgraph_agent_blueprint.graph.nodes.context_builder import context_builder_node
from langgraph_agent_blueprint.models import event
from langgraph_agent_blueprint.services import CompactionService, MemoryService
from langgraph_agent_blueprint.storage import SessionStorage


EVENT_COUNT = 1_000
MEMORY_ITERATIONS = 200


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lg-agent-perf-") as tmp:
        root = Path(tmp)
        storage = SessionStorage(root / "storage")
        project_root = root / "project"
        session_id = "perf-session"

        events = [_runtime_event(session_id, index) for index in range(EVENT_COUNT)]
        batch_seconds, _ = _measure(lambda: storage.append_events(project_root, session_id, events))
        duplicate_seconds, _ = _measure(lambda: storage.append_events(project_root, session_id, events))

        legacy_session = "legacy-session"
        legacy_dir = storage.create_session(project_root, legacy_session, {})
        legacy_events = [_runtime_event(legacy_session, index) for index in range(EVENT_COUNT)]
        (legacy_dir / "events.jsonl").write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in legacy_events),
            encoding="utf-8",
        )
        (legacy_dir / "events.index.json").unlink(missing_ok=True)
        legacy_seconds, _ = _measure(lambda: storage.append_events(project_root, legacy_session, [legacy_events[0]]))

        memory_seconds = _measure_memory_cache(root, project_root)

    rows = {
        "event_count": EVENT_COUNT,
        "memory_iterations": MEMORY_ITERATIONS,
        "batch_append_seconds": round(batch_seconds, 6),
        "duplicate_append_with_index_seconds": round(duplicate_seconds, 6),
        "legacy_missing_index_backfill_seconds": round(legacy_seconds, 6),
        **memory_seconds,
    }
    print(json.dumps(rows, indent=2, sort_keys=True))


def _runtime_event(session_id: str, index: int) -> dict[str, Any]:
    payload = event("node_finished", session_id=session_id, node="graph", data={"index": index})
    payload["id"] = f"evt-{index:04d}"
    return payload


def _measure(callback: Callable[[], Any]) -> tuple[float, Any]:
    started = time.perf_counter()
    result = callback()
    return time.perf_counter() - started, result


def _measure_memory_cache(root: Path, project_root: Path) -> dict[str, float | int]:
    memory_service = MemoryService(root / "storage")
    session_id = "memory-cache-session"
    memory_service.remember("session", "Session-scoped performance note.", session_id=session_id)
    deps = SimpleNamespace(
        hook_service=SimpleNamespace(run=lambda _context: SimpleNamespace(results=[], events=[])),
        memory_service=memory_service,
        compaction_service=CompactionService(),
    )
    state = {
        "project_root": str(project_root),
        "session_id": session_id,
        "messages": [],
        "available_tools": {},
        "available_skills": {},
        "plugin_state": {},
        "metadata": {},
        "context_status": {},
    }

    uncached_seconds, update = _measure(lambda: context_builder_node(state, deps))
    cached_state = {**state, "memory": update["memory"]}
    cached_total = 0.0
    for _ in range(MEMORY_ITERATIONS):
        seconds, _ = _measure(lambda: context_builder_node(cached_state, deps))
        cached_total += seconds

    return {
        "memory_uncached_context_build_seconds": round(uncached_seconds, 6),
        "memory_cached_context_build_total_seconds": round(cached_total, 6),
        "memory_cached_context_build_avg_seconds": round(cached_total / MEMORY_ITERATIONS, 6),
    }


if __name__ == "__main__":
    main()
