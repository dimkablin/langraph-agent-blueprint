"""SQLite-backed durable storage for normalized multi-user conversation history."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

from langgraph_agent_blueprint.models.conversations import (
    ArtifactCreate,
    ConversationCreate,
    ConversationDetail,
    ConversationListItem,
    ConversationRecord,
    MessageCreate,
    MessageRecord,
    StorageMetrics,
    StreamEventCreate,
    StreamEventRecord,
    ToolCallCreate,
    utc_now_iso,
)
from langgraph_agent_blueprint.utils.ids import new_id, validate_runtime_id

SECRET_KEYS = {"api_key", "apikey", "authorization", "access_token", "refresh_token", "token", "password", "secret"}


class ConversationNotFoundError(LookupError):
    """Raised when a user-scoped conversation row is missing or hidden."""


class SQLiteConversationStorage:
    """Durable normalized conversation storage using SQLite for local/dev deployments.

    The API is intentionally repository-shaped so a PostgreSQL implementation can be swapped
    without changing FastAPI routes or graph nodes.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._metrics = StorageMetrics()
        self._initialize()

    def create_conversation(self, user_id: str, request: ConversationCreate) -> ConversationRecord:
        now = utc_now_iso()
        conversation_id = validate_runtime_id(request.conversation_id, kind="conversation_id") if request.conversation_id else new_id("session")
        thread_id = validate_runtime_id(request.thread_id, kind="thread_id") if request.thread_id else conversation_id
        record = ConversationRecord(
            conversation_id=conversation_id,
            session_id=conversation_id,
            thread_id=thread_id,
            user_id=user_id,
            project_id=request.project_id,
            title=request.title,
            created_at=now,
            updated_at=now,
            metadata=dict(request.metadata),
        )
        with self._write() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (user_id, now, now),
            )
            conn.execute(
                """
                INSERT INTO conversations (
                    conversation_id, user_id, session_id, thread_id, project_id, title, status,
                    archived_at, deleted_at, created_at, updated_at, metadata_json, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO NOTHING
                """,
                (
                    record.conversation_id,
                    record.user_id,
                    record.session_id,
                    record.thread_id,
                    record.project_id,
                    record.title,
                    record.status,
                    record.archived_at,
                    record.deleted_at,
                    record.created_at,
                    record.updated_at,
                    json.dumps(record.metadata, ensure_ascii=False),
                    record.schema_version,
                ),
            )
        return self.get_conversation(user_id, conversation_id).conversation

    def list_conversations(self, user_id: str, *, include_archived: bool = False, limit: int = 100) -> list[ConversationListItem]:
        where = "c.user_id = ? AND c.deleted_at IS NULL"
        params: list[Any] = [user_id]
        if not include_archived:
            where += " AND c.archived_at IS NULL"
        with self._read() as conn:
            rows = conn.execute(
                f"""
                SELECT c.*, COUNT(DISTINCT m.message_id) AS message_count,
                       COUNT(DISTINCT e.event_id) AS event_count,
                       COUNT(DISTINCT t.tool_call_id) AS tool_call_count,
                       COUNT(DISTINCT a.artifact_id) AS artifact_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.conversation_id
                LEFT JOIN stream_events e ON e.conversation_id = c.conversation_id
                LEFT JOIN tool_calls t ON t.conversation_id = c.conversation_id
                LEFT JOIN artifacts a ON a.conversation_id = c.conversation_id
                WHERE {where}
                GROUP BY c.conversation_id
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [self._list_item_from_row(row) for row in rows]

    def search_conversations(self, user_id: str, query: str, *, include_archived: bool = False, limit: int = 50) -> list[ConversationListItem]:
        needle = f"%{query.strip().lower()}%"
        where = "c.user_id = ? AND c.deleted_at IS NULL AND (LOWER(COALESCE(c.title, '')) LIKE ? OR LOWER(COALESCE(m.content, '')) LIKE ?)"
        params: list[Any] = [user_id, needle, needle]
        if not include_archived:
            where += " AND c.archived_at IS NULL"
        with self._read() as conn:
            rows = conn.execute(
                f"""
                SELECT c.*, COUNT(DISTINCT m2.message_id) AS message_count,
                       COUNT(DISTINCT e.event_id) AS event_count,
                       COUNT(DISTINCT t.tool_call_id) AS tool_call_count,
                       COUNT(DISTINCT a.artifact_id) AS artifact_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.conversation_id
                LEFT JOIN messages m2 ON m2.conversation_id = c.conversation_id
                LEFT JOIN stream_events e ON e.conversation_id = c.conversation_id
                LEFT JOIN tool_calls t ON t.conversation_id = c.conversation_id
                LEFT JOIN artifacts a ON a.conversation_id = c.conversation_id
                WHERE {where}
                GROUP BY c.conversation_id
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [self._list_item_from_row(row) for row in rows]

    def get_conversation(self, user_id: str, conversation_id: str) -> ConversationDetail:
        safe_id = validate_runtime_id(conversation_id, kind="conversation_id")
        with self._read() as conn:
            conversation = conn.execute(
                "SELECT * FROM conversations WHERE conversation_id = ? AND user_id = ? AND deleted_at IS NULL",
                (safe_id, user_id),
            ).fetchone()
            if conversation is None:
                raise ConversationNotFoundError(safe_id)
            return self._detail_for_conversation_row(conn, user_id, conversation)

    def get_conversation_for_thread(self, user_id: str, *, session_id: str | None = None, thread_id: str | None = None) -> ConversationDetail:
        if not session_id and not thread_id:
            raise ConversationNotFoundError("<missing>")
        clauses = ["user_id = ?", "deleted_at IS NULL"]
        params: list[Any] = [user_id]
        if session_id:
            clauses.append("session_id = ?")
            params.append(validate_runtime_id(session_id, kind="session_id"))
        if thread_id:
            clauses.append("thread_id = ?")
            params.append(validate_runtime_id(thread_id, kind="thread_id"))
        with self._read() as conn:
            conversation = conn.execute(
                f"SELECT * FROM conversations WHERE {' AND '.join(clauses)}",
                tuple(params),
            ).fetchone()
            if conversation is None:
                raise ConversationNotFoundError(session_id or thread_id or "<missing>")
            return self._detail_for_conversation_row(conn, user_id, conversation)

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> ConversationRecord:
        clean_title = title.strip()[:200]
        if not clean_title:
            raise ValueError("Conversation title cannot be empty")
        self._update_owned_conversation(user_id, conversation_id, "title = ?, updated_at = ?", clean_title, utc_now_iso())
        return self.get_conversation(user_id, conversation_id).conversation

    def archive_conversation(self, user_id: str, conversation_id: str) -> ConversationRecord:
        now = utc_now_iso()
        self._update_owned_conversation(user_id, conversation_id, "status = 'archived', archived_at = ?, updated_at = ?", now, now)
        return self.get_conversation(user_id, conversation_id).conversation

    def soft_delete_conversation(self, user_id: str, conversation_id: str) -> None:
        now = utc_now_iso()
        self._update_owned_conversation(user_id, conversation_id, "status = 'deleted', deleted_at = ?, updated_at = ?", now, now)

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
        safe_id = validate_runtime_id(conversation_id, kind="conversation_id")
        now = utc_now_iso()
        with self._write() as conn:
            if not self._conversation_exists(conn, user_id, safe_id):
                raise ConversationNotFoundError(safe_id)
            message_index = self._next_order(conn, "messages", safe_id)
            for message in [item for item in [user_message, assistant_message] if item is not None]:
                self._insert_message(conn, user_id, safe_id, message, message_index, now)
                message_index += 1
            event_index = self._next_order(conn, "stream_events", safe_id)
            for stream_event in events or []:
                self._insert_event(conn, user_id, safe_id, stream_event, event_index, now)
                event_index += 1
            tool_index = self._next_order(conn, "tool_calls", safe_id)
            for tool_call in tool_calls or []:
                self._insert_tool_call(conn, user_id, safe_id, tool_call, tool_index, now)
                tool_index += 1
            for artifact in artifacts or []:
                self._insert_artifact(conn, user_id, safe_id, artifact, now)
            conn.execute("UPDATE conversations SET updated_at = ? WHERE conversation_id = ? AND user_id = ?", (now, safe_id, user_id))
        return self.get_conversation(user_id, safe_id)

    def metrics_snapshot(self) -> StorageMetrics:
        return self._metrics.model_copy()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        start = perf_counter()
        with self._connect() as conn:
            try:
                yield conn
            finally:
                self._metrics.read_count += 1
                self._metrics.last_read_latency_ms = (perf_counter() - start) * 1000

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        start = perf_counter()
        with self._connect() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self._metrics.write_count += 1
                self._metrics.last_write_latency_ms = (perf_counter() - start) * 1000

    def _update_owned_conversation(self, user_id: str, conversation_id: str, set_sql: str, *params: Any) -> None:
        safe_id = validate_runtime_id(conversation_id, kind="conversation_id")
        with self._write() as conn:
            cursor = conn.execute(
                f"UPDATE conversations SET {set_sql} WHERE conversation_id = ? AND user_id = ? AND deleted_at IS NULL",
                (*params, safe_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ConversationNotFoundError(safe_id)

    @staticmethod
    def _conversation_exists(conn: sqlite3.Connection, user_id: str, conversation_id: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM conversations WHERE conversation_id = ? AND user_id = ? AND deleted_at IS NULL",
            (conversation_id, user_id),
        ).fetchone() is not None

    @staticmethod
    def _next_order(conn: sqlite3.Connection, table: str, conversation_id: str) -> int:
        row = conn.execute(f"SELECT COALESCE(MAX(order_index), -1) + 1 AS next_order FROM {table} WHERE conversation_id = ?", (conversation_id,)).fetchone()
        return int(row["next_order"])

    @staticmethod
    def _insert_message(conn: sqlite3.Connection, user_id: str, conversation_id: str, message: MessageCreate, order_index: int, now: str) -> None:
        message_id = validate_runtime_id(message.message_id, kind="message_id") if message.message_id else new_id("msg")
        conn.execute(
            """
            INSERT OR IGNORE INTO messages (message_id, conversation_id, user_id, role, content, order_index, idempotency_key, created_at, updated_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, conversation_id, user_id, message.role, message.content, order_index, message.idempotency_key, now, now, json.dumps(redact_secrets(message.metadata), ensure_ascii=False)),
        )

    @staticmethod
    def _insert_event(conn: sqlite3.Connection, user_id: str, conversation_id: str, event: StreamEventCreate, order_index: int, now: str) -> None:
        event_id = validate_runtime_id(event.event_id, kind="event_id") if event.event_id else new_id("event")
        conn.execute(
            """
            INSERT INTO stream_events (event_id, conversation_id, user_id, type, order_index, created_at, payload_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id, event_id) DO NOTHING
            """,
            (event_id, conversation_id, user_id, event.type, order_index, now, json.dumps(redact_secrets(event.payload), ensure_ascii=False), json.dumps(redact_secrets(event.metadata), ensure_ascii=False)),
        )

    @staticmethod
    def _insert_tool_call(conn: sqlite3.Connection, user_id: str, conversation_id: str, tool_call: ToolCallCreate, order_index: int, now: str) -> None:
        tool_call_id = validate_runtime_id(tool_call.tool_call_id, kind="tool_call_id") if tool_call.tool_call_id else new_id("tool")
        output_json = json.dumps(redact_secrets(tool_call.output), ensure_ascii=False) if tool_call.output is not None else None
        conn.execute(
            """
            INSERT OR IGNORE INTO tool_calls (tool_call_id, conversation_id, user_id, name, status, order_index, input_json, output_json, idempotency_key, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tool_call_id, conversation_id, user_id, tool_call.name, tool_call.status, order_index, json.dumps(redact_secrets(tool_call.input), ensure_ascii=False), output_json, tool_call.idempotency_key, now, json.dumps(redact_secrets(tool_call.metadata), ensure_ascii=False)),
        )

    @staticmethod
    def _insert_artifact(conn: sqlite3.Connection, user_id: str, conversation_id: str, artifact: ArtifactCreate, now: str) -> None:
        artifact_id = validate_runtime_id(artifact.artifact_id, kind="artifact_id") if artifact.artifact_id else new_id("artifact")
        conn.execute(
            """
            INSERT INTO artifacts (artifact_id, conversation_id, user_id, kind, uri, title, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO NOTHING
            """,
            (artifact_id, conversation_id, user_id, artifact.kind, artifact.uri, artifact.title, now, json.dumps(redact_secrets(artifact.metadata), ensure_ascii=False)),
        )

    def _detail_for_conversation_row(self, conn: sqlite3.Connection, user_id: str, conversation: sqlite3.Row) -> ConversationDetail:
        conversation_id = conversation["conversation_id"]
        messages = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? AND user_id = ? ORDER BY order_index ASC, created_at ASC",
            (conversation_id, user_id),
        ).fetchall()
        events = conn.execute(
            "SELECT * FROM stream_events WHERE conversation_id = ? AND user_id = ? ORDER BY order_index ASC, created_at ASC",
            (conversation_id, user_id),
        ).fetchall()
        tool_calls = conn.execute(
            "SELECT * FROM tool_calls WHERE conversation_id = ? AND user_id = ? ORDER BY order_index ASC, created_at ASC",
            (conversation_id, user_id),
        ).fetchall()
        artifacts = conn.execute(
            "SELECT * FROM artifacts WHERE conversation_id = ? AND user_id = ? ORDER BY created_at ASC",
            (conversation_id, user_id),
        ).fetchall()
        return ConversationDetail(
            conversation=self._conversation_from_row(conversation),
            messages=[self._message_from_row(row) for row in messages],
            events=[self._event_from_row(row) for row in events],
            tool_calls=[self._json_row(row, "input_json", "output_json", "metadata_json") for row in tool_calls],
            artifacts=[self._json_row(row, "metadata_json") for row in artifacts],
        )

    @staticmethod
    def _conversation_from_row(row: sqlite3.Row) -> ConversationRecord:
        return ConversationRecord(
            conversation_id=row["conversation_id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            thread_id=row["thread_id"],
            project_id=row["project_id"],
            title=row["title"],
            status=row["status"],
            archived_at=row["archived_at"],
            deleted_at=row["deleted_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata_json"] or "{}"),
            schema_version=row["schema_version"],
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> MessageRecord:
        return MessageRecord(
            message_id=row["message_id"], conversation_id=row["conversation_id"], user_id=row["user_id"], role=row["role"],
            content=row["content"], order_index=row["order_index"], idempotency_key=row["idempotency_key"], created_at=row["created_at"],
            updated_at=row["updated_at"], metadata=json.loads(row["metadata_json"] or "{}"),
        )

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> StreamEventRecord:
        return StreamEventRecord(
            event_id=row["event_id"], conversation_id=row["conversation_id"], user_id=row["user_id"], type=row["type"],
            order_index=row["order_index"], created_at=row["created_at"], payload=json.loads(row["payload_json"] or "{}"),
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    @staticmethod
    def _list_item_from_row(row: sqlite3.Row) -> ConversationListItem:
        return ConversationListItem(
            conversation_id=row["conversation_id"], session_id=row["session_id"], thread_id=row["thread_id"], title=row["title"],
            status=row["status"], project_id=row["project_id"], message_count=row["message_count"], event_count=row["event_count"],
            tool_call_count=row["tool_call_count"], artifact_count=row["artifact_count"], created_at=row["created_at"], updated_at=row["updated_at"],
        )

    @staticmethod
    def _json_row(row: sqlite3.Row, *json_columns: str) -> dict[str, Any]:
        data = dict(row)
        for column in json_columns:
            if column in data:
                value = data.pop(column)
                data[column.removesuffix("_json")] = json.loads(value) if value else ({} if column != "output_json" else None)
        return data


def redact_secrets(value: Any) -> Any:
    """Recursively redact known secret-bearing keys before durable persistence."""

    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key).lower() in SECRET_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    project_id TEXT,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    archived_at TEXT,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    schema_version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations(user_id, deleted_at, archived_at, updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_user_thread ON conversations(user_id, thread_id);
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    idempotency_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_order ON messages(conversation_id, order_index);
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_idempotency ON messages(conversation_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE TABLE IF NOT EXISTS stream_events (
    event_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (conversation_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_stream_events_conversation_order ON stream_events(conversation_id, order_index);
CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT,
    idempotency_key TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_tool_calls_conversation_order ON tool_calls(conversation_id, order_index);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tool_calls_idempotency ON tool_calls(conversation_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    uri TEXT NOT NULL,
    title TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_artifacts_conversation ON artifacts(conversation_id, created_at);
CREATE TABLE IF NOT EXISTS checkpoint_refs (
    checkpoint_ref_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT,
    checkpoint_id TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_checkpoint_refs_conversation ON checkpoint_refs(conversation_id, created_at DESC);
"""
