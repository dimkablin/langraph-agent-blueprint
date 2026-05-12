"""Filesystem-backed persistence for sessions, messages, events, tool calls, todos, and memory refs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ValidationError

from langgraph_agent_blueprint.models import (
    ChildRunMetadata,
    FileSnapshotRecord,
    RollbackResult,
    RuntimeEvent,
    SessionMetadata,
    SubagentResult,
    ToolResult,
    dump_model,
)
from langgraph_agent_blueprint.utils.ids import validate_runtime_id, validate_session_id
from langgraph_agent_blueprint.utils.paths import ensure_dir, resolve_under_root
from langgraph_agent_blueprint.utils.serialization import message_from_dict, message_to_dict

from .paths import project_storage_dir


class SessionStorage:
    """Filesystem-backed session/event/tool-call storage."""

    def __init__(self, storage_dir: str | Path) -> None:
        self.storage_dir = Path(storage_dir)

    def session_dir(self, project_root: str | Path, session_id: str) -> Path:
        safe_id = validate_session_id(session_id)
        sessions_root = (project_storage_dir(self.storage_dir, project_root) / "sessions").resolve()
        candidate = (sessions_root / safe_id).resolve()
        try:
            candidate.relative_to(sessions_root)
        except ValueError as exc:
            raise ValueError("Resolved session path escaped the sessions root") from exc
        return candidate

    def create_session(self, project_root: str | Path, session_id: str, metadata: dict[str, Any]) -> Path:
        """Create or update a session directory while preserving existing metadata fields."""

        session_dir = ensure_dir(self.session_dir(project_root, session_id))
        ensure_dir(session_dir / "exports")
        ensure_dir(session_dir / "large_outputs")
        metadata_path = session_dir / "metadata.json"
        now = datetime.now(timezone.utc).isoformat()
        if metadata_path.exists():
            try:
                current = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                current = {}
        else:
            current = {
                "session_id": session_id,
                "project_root": str(Path(project_root).resolve()),
                "created_at": now,
            }
        current.setdefault("session_id", session_id)
        current.setdefault("project_root", str(Path(project_root).resolve()))
        current.update(metadata)
        current["updated_at"] = now
        current = SessionMetadata.from_record(current).to_record()
        metadata_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        (session_dir / "events.jsonl").touch(exist_ok=True)
        (session_dir / "tool_calls.jsonl").touch(exist_ok=True)
        return session_dir

    def child_run_dir(self, project_root: str | Path, parent_session_id: str, child_run_id: str) -> Path:
        """Return a confined child-run directory under a validated parent session."""

        safe_child_id = validate_runtime_id(child_run_id, kind="child_run_id")
        parent_dir = self.session_dir(project_root, parent_session_id)
        child_root = (parent_dir / "child_runs").resolve()
        candidate = (child_root / safe_child_id).resolve()
        try:
            candidate.relative_to(child_root)
        except ValueError as exc:
            raise ValueError("Resolved child run path escaped the child_runs root") from exc
        return candidate

    def save_child_run(
        self,
        project_root: str | Path,
        parent_session_id: str,
        metadata: dict[str, Any],
        result: dict[str, Any],
        events: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Persist child-run metadata, result, and optional child event transcript."""

        metadata_payload = dump_model(ChildRunMetadata.model_validate(metadata))
        result_payload = dump_model(SubagentResult.model_validate(result))
        child_dir = ensure_dir(self.child_run_dir(project_root, parent_session_id, metadata_payload["child_run_id"]))
        (child_dir / "metadata.json").write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (child_dir / "result.json").write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if events is not None:
            with (child_dir / "events.jsonl").open("w", encoding="utf-8") as handle:
                for item in events:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        return child_dir

    def list_child_runs(self, project_root: str | Path, parent_session_id: str) -> list[dict[str, Any]]:
        """List persisted child-run metadata/result summaries for one parent session."""

        child_root = self.session_dir(project_root, parent_session_id) / "child_runs"
        if not child_root.exists():
            return []
        rows: list[dict[str, Any]] = []
        for child_dir in child_root.iterdir():
            if not child_dir.is_dir():
                continue
            try:
                metadata = json.loads((child_dir / "metadata.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            result = {}
            result_path = child_dir / "result.json"
            if result_path.exists():
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    result = {}
            rows.append({"metadata": metadata, "result": result})
        return sorted(rows, key=lambda item: item.get("metadata", {}).get("started_at", ""))

    def load_child_run(self, project_root: str | Path, parent_session_id: str, child_run_id: str) -> dict[str, Any]:
        """Load one persisted child-run metadata/result/events record."""

        child_dir = self.child_run_dir(project_root, parent_session_id, child_run_id)
        metadata = json.loads((child_dir / "metadata.json").read_text(encoding="utf-8"))
        result_path = child_dir / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        events = self._read_jsonl(child_dir / "events.jsonl", RuntimeEvent)
        return {"metadata": metadata, "result": result, "events": events}

    def append_event(self, project_root: str | Path, session_id: str, event: dict[str, Any]) -> None:
        """Append a session event once, deduplicating by event id when available."""

        session_dir = self.create_session(project_root, session_id, {})
        payload = dump_model(RuntimeEvent.model_validate(event))
        event_id = payload.get("id")
        if event_id:
            for existing in self._read_jsonl(session_dir / "events.jsonl"):
                if existing.get("id") == event_id:
                    return
        with (session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def append_tool_call(self, project_root: str | Path, session_id: str, record: dict[str, Any]) -> None:
        session_dir = self.create_session(project_root, session_id, {})
        payload = dump_model(ToolResult.model_validate(record))
        with (session_dir / "tool_calls.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def save_file_snapshot(self, project_root: str | Path, session_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Persist a pre-edit file snapshot for later public rollback."""

        session_dir = self.create_session(project_root, session_id, {})
        payload = dump_model(FileSnapshotRecord.model_validate(snapshot))
        snapshots = self.list_file_snapshots(project_root, session_id)
        snapshots.append(payload)
        self._write_file_snapshots(session_dir, snapshots)
        return payload

    def list_file_snapshots(self, project_root: str | Path, session_id: str) -> list[dict[str, Any]]:
        """Load persisted file snapshots for one session."""

        path = self._file_snapshots_path(project_root, session_id)
        if not path.exists():
            return []
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(rows, list):
            return []
        snapshots = []
        for item in rows:
            try:
                snapshots.append(dump_model(FileSnapshotRecord.model_validate(item)))
            except (TypeError, ValueError, ValidationError):
                continue
        return snapshots

    def load_file_snapshot(self, project_root: str | Path, session_id: str, snapshot_id: str) -> dict[str, Any]:
        """Load a single persisted file snapshot by public snapshot id."""

        safe_snapshot_id = validate_runtime_id(snapshot_id, kind="snapshot_id")
        for snapshot in self.list_file_snapshots(project_root, session_id):
            if snapshot.get("snapshot_id") == safe_snapshot_id:
                return snapshot
        raise FileNotFoundError(f"File snapshot not found: {safe_snapshot_id}")

    def restore_file_snapshot(
        self,
        project_root: str | Path,
        session_id: str,
        snapshot_id: str | None = None,
    ) -> RollbackResult:
        """Restore the latest available snapshot, or a specific snapshot when requested."""

        snapshots = self.list_file_snapshots(project_root, session_id)
        selected = self._select_snapshot(snapshots, snapshot_id)
        if selected is None:
            return RollbackResult(status="not_available", message="No available file snapshot to rollback.")
        try:
            root = Path(project_root).resolve()
            target = resolve_under_root(selected["path"], root)
            if selected.get("existed"):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(selected.get("content") or ""), encoding=selected.get("encoding") or "utf-8")
            elif target.exists():
                if not target.is_file():
                    return RollbackResult(
                        status="error",
                        message=f"Rollback target is not a file: {selected['path']}",
                        snapshot_id=selected["snapshot_id"],
                        path=selected["path"],
                    )
                target.unlink()
        except (OSError, ValueError) as exc:
            return RollbackResult(
                status="error",
                message=str(exc),
                snapshot_id=selected.get("snapshot_id"),
                path=selected.get("path"),
            )
        restored_at = datetime.now(timezone.utc).isoformat()
        updated = []
        for item in snapshots:
            if item.get("snapshot_id") == selected["snapshot_id"]:
                item = {**item, "restored_at": restored_at}
            updated.append(item)
        self._write_file_snapshots(self.session_dir(project_root, session_id), updated)
        return RollbackResult(
            status="restored",
            message=f"Rollback restored {selected['path']} from snapshot {selected['snapshot_id']}.",
            snapshot_id=selected["snapshot_id"],
            path=selected["path"],
        )

    def save_messages(self, project_root: str | Path, session_id: str, messages: list[BaseMessage]) -> None:
        session_dir = self.create_session(project_root, session_id, {})
        (session_dir / "messages.json").write_text(
            json.dumps([message_to_dict(message) for message in messages], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_json(self, project_root: str | Path, session_id: str, name: str, data: Any) -> None:
        session_dir = self.create_session(project_root, session_id, {})
        (session_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_session(self, project_root: str | Path, session_id: str) -> dict[str, Any]:
        """Load persisted session metadata, messages, events, tool calls, todos, memory, and usage."""

        session_dir = self.session_dir(project_root, session_id)
        metadata = SessionMetadata.from_record(json.loads((session_dir / "metadata.json").read_text(encoding="utf-8"))).to_record()
        messages_path = session_dir / "messages.json"
        messages = []
        if messages_path.exists():
            messages = [message_from_dict(item) for item in json.loads(messages_path.read_text(encoding="utf-8"))]
        events = self._read_jsonl(session_dir / "events.jsonl", RuntimeEvent)
        tool_calls = self._read_jsonl(session_dir / "tool_calls.jsonl", ToolResult)
        todos_path = session_dir / "todos.json"
        memory_refs_path = session_dir / "memory_refs.json"
        todos = json.loads(todos_path.read_text(encoding="utf-8")) if todos_path.exists() else []
        memory_refs = json.loads(memory_refs_path.read_text(encoding="utf-8")) if memory_refs_path.exists() else {}
        return {
            "metadata": metadata,
            "messages": messages,
            "events": events,
            "tool_calls": tool_calls,
            "todos": todos,
            "memory": memory_refs,
            "usage": metadata.get("usage", {}),
        }

    def list_sessions(self, project_root: str | Path | None = None) -> list[dict[str, Any]]:
        """List session metadata for one project root or every stored project, newest first."""

        roots = [project_storage_dir(self.storage_dir, project_root)] if project_root else list((self.storage_dir / "projects").glob("*"))
        sessions: list[dict[str, Any]] = []
        for root in roots:
            for metadata_path in root.glob("sessions/*/metadata.json"):
                try:
                    sessions.append(json.loads(metadata_path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        return sorted(sessions, key=lambda item: item.get("updated_at", ""), reverse=True)

    def clear_session(self, project_root: str | Path, session_id: str) -> None:
        session_dir = self.create_session(project_root, session_id, {})
        (session_dir / "events.jsonl").write_text("", encoding="utf-8")
        (session_dir / "tool_calls.jsonl").write_text("", encoding="utf-8")
        (session_dir / "messages.json").write_text("[]", encoding="utf-8")

    def rewind_session(self, project_root: str | Path, session_id: str, keep_last: int) -> list[BaseMessage]:
        loaded = self.load_session(project_root, session_id)
        messages = loaded["messages"][:-keep_last] if keep_last else []
        self.save_messages(project_root, session_id, messages)
        return messages

    @staticmethod
    def _read_jsonl(path: Path, model_cls: type[BaseModel] | None = None) -> list[dict[str, Any]]:
        """Read JSONL records, optionally validating each record and skipping corrupt rows."""

        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if model_cls is not None:
                    payload = dump_model(model_cls.model_validate(payload))
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
                continue
            rows.append(payload)
        return rows

    def _file_snapshots_path(self, project_root: str | Path, session_id: str) -> Path:
        return self.session_dir(project_root, session_id) / "file_snapshots.json"

    @staticmethod
    def _write_file_snapshots(session_dir: Path, snapshots: list[dict[str, Any]]) -> None:
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / "file_snapshots.json"
        path.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _select_snapshot(snapshots: list[dict[str, Any]], snapshot_id: str | None) -> dict[str, Any] | None:
        if snapshot_id is not None:
            safe_snapshot_id = validate_runtime_id(snapshot_id, kind="snapshot_id")
            for snapshot in snapshots:
                if snapshot.get("snapshot_id") == safe_snapshot_id and snapshot.get("restored_at") is None:
                    return snapshot
            return None
        for snapshot in reversed(snapshots):
            if snapshot.get("restored_at") is None:
                return snapshot
        return None
