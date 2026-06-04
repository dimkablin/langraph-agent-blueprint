"""Durable LangGraph checkpoint helpers for interrupt/resume state."""

from __future__ import annotations

import pickle
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from langgraph.checkpoint.memory import InMemorySaver


class SQLiteCheckpointSaver(InMemorySaver):
    """Small SQLite-backed checkpoint saver compatible with LangGraph's memory saver.

    LangGraph's bundled :class:`InMemorySaver` has the semantics this runtime already uses
    for interrupts, writes, and thread deletion, but it loses pending approval checkpoints
    when the API process restarts. This saver keeps the same in-process shape and snapshots
    it to SQLite after every write so a new runtime instance can resume interrupted threads.
    """

    def __init__(self, database_path: str | Path) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
        self._load_snapshot()

    def put(self, config: dict[str, Any], checkpoint: dict[str, Any], metadata: dict[str, Any], new_versions: dict[str, Any]) -> dict[str, Any]:
        result = super().put(config, checkpoint, metadata, new_versions)
        self._save_snapshot()
        return result

    def put_writes(self, config: dict[str, Any], writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        super().put_writes(config, writes, task_id, task_path)
        self._save_snapshot()

    def delete_thread(self, thread_id: str) -> None:
        super().delete_thread(thread_id)
        self._save_snapshot()

    def _initialize_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
                    key TEXT PRIMARY KEY,
                    payload BLOB NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def _load_snapshot(self) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM langgraph_checkpoints WHERE key = 'snapshot'").fetchone()
        if row is None:
            return
        snapshot = pickle.loads(row[0])
        self.storage = _storage_from_plain(snapshot.get("storage", {}))
        self.writes = defaultdict(dict, snapshot.get("writes", {}))
        self.blobs = dict(snapshot.get("blobs", {}))

    def _save_snapshot(self) -> None:
        payload = pickle.dumps(
            {
                "storage": _plain_storage(self.storage),
                "writes": dict(self.writes),
                "blobs": dict(self.blobs),
            },
            protocol=pickle.HIGHEST_PROTOCOL,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO langgraph_checkpoints (key, payload, updated_at)
                VALUES ('snapshot', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (payload,),
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)


def default_checkpointer(database_path: str | Path | None = None) -> InMemorySaver:
    """Return the default checkpointer used for interrupt/resume.

    A database path enables durable checkpoint resume across runtime/server restarts. Tests
    may omit it to keep an isolated in-memory saver.
    """

    if database_path is None:
        return InMemorySaver()
    return SQLiteCheckpointSaver(database_path)


def _plain_storage(storage: defaultdict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, dict[str, Any]]]:
    return {thread_id: {namespace: dict(checkpoints) for namespace, checkpoints in namespaces.items()} for thread_id, namespaces in storage.items()}


def _storage_from_plain(data: dict[str, dict[str, dict[str, Any]]]) -> defaultdict[str, defaultdict[str, dict[str, Any]]]:
    storage: defaultdict[str, defaultdict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
    for thread_id, namespaces in data.items():
        storage[thread_id] = defaultdict(dict, {namespace: dict(checkpoints) for namespace, checkpoints in namespaces.items()})
    return storage
