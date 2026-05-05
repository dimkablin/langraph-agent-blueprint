from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage

from claude_code_langgraph.utils.paths import ensure_dir
from claude_code_langgraph.utils.serialization import message_from_dict, message_to_dict

from .paths import project_storage_dir


class SessionStorage:
    """Filesystem-backed session/event/tool-call storage."""

    def __init__(self, storage_dir: str | Path) -> None:
        self.storage_dir = Path(storage_dir)

    def session_dir(self, project_root: str | Path, session_id: str) -> Path:
        return project_storage_dir(self.storage_dir, project_root) / "sessions" / session_id

    def create_session(self, project_root: str | Path, session_id: str, metadata: dict[str, Any]) -> Path:
        session_dir = ensure_dir(self.session_dir(project_root, session_id))
        ensure_dir(session_dir / "exports")
        ensure_dir(session_dir / "large_outputs")
        metadata_path = session_dir / "metadata.json"
        current = {
            "session_id": session_id,
            "project_root": str(Path(project_root).resolve()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        current.update(metadata)
        metadata_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        (session_dir / "events.jsonl").touch(exist_ok=True)
        (session_dir / "tool_calls.jsonl").touch(exist_ok=True)
        return session_dir

    def append_event(self, project_root: str | Path, session_id: str, event: dict[str, Any]) -> None:
        session_dir = self.create_session(project_root, session_id, {})
        with (session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def append_tool_call(self, project_root: str | Path, session_id: str, record: dict[str, Any]) -> None:
        session_dir = self.create_session(project_root, session_id, {})
        with (session_dir / "tool_calls.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

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
        session_dir = self.session_dir(project_root, session_id)
        metadata = json.loads((session_dir / "metadata.json").read_text(encoding="utf-8"))
        messages_path = session_dir / "messages.json"
        messages = []
        if messages_path.exists():
            messages = [message_from_dict(item) for item in json.loads(messages_path.read_text(encoding="utf-8"))]
        events = self._read_jsonl(session_dir / "events.jsonl")
        tool_calls = self._read_jsonl(session_dir / "tool_calls.jsonl")
        return {"metadata": metadata, "messages": messages, "events": events, "tool_calls": tool_calls}

    def list_sessions(self, project_root: str | Path | None = None) -> list[dict[str, Any]]:
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
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

