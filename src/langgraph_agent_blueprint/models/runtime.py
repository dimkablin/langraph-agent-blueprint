"""Public Pydantic contracts for invoking and validating agent runtime turns."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator

from langgraph_agent_blueprint.utils.ids import validate_session_id, validate_thread_id

from .base import RuntimeModel


AgentRunMode = Literal["default", "plan"]
AgentRunAction = Literal["run", "rollback"]
AgentRunStatus = Literal["success", "error", "blocked"]
VerificationStatus = Literal["passed", "failed", "not run"]
RollbackStatus = Literal["restored", "not_available", "error"]


class FileSnapshotInfo(RuntimeModel):
    """Public metadata for a file snapshot captured before a mutating tool call."""

    snapshot_id: str
    path: str
    existed: bool
    tool_call_id: str | None = None
    tool_name: str | None = None
    created_at: str | None = None
    restored_at: str | None = None


class FileSnapshotRecord(FileSnapshotInfo):
    """Persisted file snapshot with the previous file content needed for rollback."""

    session_id: str
    content: str | None = None
    encoding: str = "utf-8"

    def public_info(self) -> FileSnapshotInfo:
        return FileSnapshotInfo.model_validate(self.model_dump(exclude={"session_id", "content", "encoding"}))


class RollbackResult(RuntimeModel):
    """Public result for an explicit file rollback request."""

    status: RollbackStatus
    message: str
    snapshot_id: str | None = None
    path: str | None = None


class AgentRunInput(RuntimeModel):
    """Public runtime request used by tests and embedders that call the graph directly."""

    message: str
    action: AgentRunAction = "run"
    project_id: str | None = None
    project_root: str | None = None
    input_kind: Literal["interactive", "headless", "command"] = "headless"
    mode: AgentRunMode = "default"
    session_id: str | None = None
    thread_id: str | None = None
    rollback_snapshot_id: str | None = None
    model_intelligence: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str | None) -> str | None:
        return validate_session_id(value) if value is not None else None

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, value: str | None) -> str | None:
        return validate_thread_id(value) if value is not None else None


class AgentRunOutput(RuntimeModel):
    """Public terminal outcome for one graph/runtime turn."""

    status: AgentRunStatus
    final_response: str = ""
    changed_files: list[str] = Field(default_factory=list)
    project_id: str | None = None
    project_root: str | None = None
    git_branch: str | None = None
    git_dirty: bool = False
    verification_commands: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = "not run"
    error_message: str | None = None
    session_id: str
    thread_id: str
    snapshots: list[FileSnapshotInfo] = Field(default_factory=list)
    rollback_available: bool = False
    rollback_result: RollbackResult | None = None
    permission_required: dict[str, Any] | None = None
    todos: list[dict[str, Any]] = Field(default_factory=list)
    context_compacted: bool = False
    events: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_graph_result(cls, result: dict[str, Any]) -> "AgentRunOutput":
        """Create the public terminal contract from the graph's persisted state shape."""

        tool_results = list(result.get("tool_results", []) or [])
        errors = list(result.get("errors", []) or [])
        status = _status_from_state(result, tool_results, errors)
        verification_commands = _verification_commands(tool_results)
        snapshots = _snapshots(result, tool_results)
        return cls(
            status=status,
            final_response=str(result.get("final_response") or ""),
            changed_files=_changed_files(tool_results, result.get("project_root")),
            project_id=str(result.get("project_id") or "") or None,
            project_root=str(result.get("project_root") or "") or None,
            git_branch=_git_branch(result),
            git_dirty=_git_dirty(result),
            verification_commands=verification_commands,
            verification_status=_verification_status(tool_results, verification_commands),
            error_message=_error_message(result, tool_results, errors),
            session_id=str(result.get("session_id") or ""),
            thread_id=str(result.get("thread_id") or ""),
            snapshots=snapshots,
            rollback_available=_rollback_available(snapshots),
            permission_required=result.get("pending_confirmation"),
            todos=list(result.get("todos", []) or []),
            context_compacted=_context_compacted(result),
            events=list(result.get("ui_events", []) or []),
        )


def _status_from_state(result: dict[str, Any], tool_results: list[dict[str, Any]], errors: list[dict[str, Any]]) -> AgentRunStatus:
    if result.get("__interrupt__") or result.get("pending_confirmation"):
        return "blocked"
    if any(item.get("status") == "rejected" for item in tool_results):
        return "blocked"
    if errors:
        return "error"
    if result.get("final_response"):
        return "success"
    latest_tool_result = tool_results[-1] if tool_results else {}
    if latest_tool_result.get("status") == "error":
        return "error"
    return "success"


def _changed_files(tool_results: list[dict[str, Any]], project_root: Any) -> list[str]:
    paths: list[str] = []
    root = Path(project_root).resolve() if project_root else None
    for result in tool_results:
        if result.get("name") not in {"write_file", "edit_file", "notebook_edit"}:
            continue
        output = result.get("output") if isinstance(result.get("output"), dict) else {}
        path = output.get("path") or result.get("metadata", {}).get("path")
        if not path:
            continue
        paths.append(_display_path(path, root))
    return _unique(paths)


def _git_branch(result: dict[str, Any]) -> str | None:
    workspace = result.get("workspace") if isinstance(result.get("workspace"), dict) else {}
    branch = workspace.get("current_branch")
    return str(branch) if branch else None


def _git_dirty(result: dict[str, Any]) -> bool:
    workspace = result.get("workspace") if isinstance(result.get("workspace"), dict) else {}
    return bool(workspace.get("dirty"))


def _verification_commands(tool_results: list[dict[str, Any]]) -> list[str]:
    commands = []
    for result in tool_results:
        if result.get("name") not in {"bash", "powershell"}:
            continue
        output = result.get("output") if isinstance(result.get("output"), dict) else {}
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        command = output.get("command") or metadata.get("command")
        if command:
            commands.append(str(command))
    return _unique(commands)


def _verification_status(tool_results: list[dict[str, Any]], commands: list[str]) -> VerificationStatus:
    if not commands:
        return "not run"
    shell_results = [item for item in tool_results if item.get("name") in {"bash", "powershell"}]
    if shell_results and shell_results[-1].get("status") == "error":
        return "failed"
    return "passed"


def _error_message(
    result: dict[str, Any],
    tool_results: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> str | None:
    if result.get("pending_confirmation"):
        return str(result["pending_confirmation"].get("reason") or "Permission required.")
    if _status_from_state(result, tool_results, errors) == "success":
        return None
    if errors:
        return str(errors[-1].get("message") or errors[-1])
    failed = [item for item in tool_results if item.get("status") in {"error", "rejected"}]
    if failed:
        return str(failed[-1].get("content") or failed[-1].get("error") or "")
    return None


def _snapshots(result: dict[str, Any], tool_results: list[dict[str, Any]]) -> list[FileSnapshotInfo]:
    records: list[FileSnapshotInfo] = []
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    for item in metadata.get("file_snapshots", []) or []:
        records.append(_snapshot_info(item))
    for tool_result in tool_results:
        item_metadata = tool_result.get("metadata") if isinstance(tool_result.get("metadata"), dict) else {}
        if "snapshot" in item_metadata:
            records.append(_snapshot_info(item_metadata["snapshot"]))
    return _unique_snapshots(records)


def _snapshot_info(value: Any) -> FileSnapshotInfo:
    if isinstance(value, FileSnapshotRecord):
        return value.public_info()
    if isinstance(value, dict) and "session_id" in value:
        return FileSnapshotRecord.model_validate(value).public_info()
    return FileSnapshotInfo.model_validate(value)


def _rollback_available(snapshots: list[FileSnapshotInfo]) -> bool:
    return any(snapshot.restored_at is None for snapshot in snapshots)


def _context_compacted(result: dict[str, Any]) -> bool:
    context_status = result.get("context_status") if isinstance(result.get("context_status"), dict) else {}
    if context_status.get("compacted"):
        return True
    return any(item.get("type") == "compact_finished" for item in result.get("ui_events", []) or [])


def _display_path(path: Any, root: Path | None) -> str:
    candidate = Path(str(path))
    if root is not None:
        try:
            return candidate.resolve().relative_to(root).as_posix()
        except (OSError, ValueError):
            pass
    return candidate.as_posix()


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    return unique_items


def _unique_snapshots(items: list[FileSnapshotInfo]) -> list[FileSnapshotInfo]:
    seen: set[str] = set()
    unique_items: list[FileSnapshotInfo] = []
    for item in items:
        if item.snapshot_id not in seen:
            seen.add(item.snapshot_id)
            unique_items.append(item)
    return unique_items
