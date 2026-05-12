"""FastAPI session routes for listing and loading persisted graph sessions."""

from typing import Annotated

from fastapi import APIRouter, Path, Request

from .schemas import (
    ChildRunDetailDTO,
    ChildRunListItemDTO,
    ContextStateDTO,
    ExportRecordDTO,
    ExportRequest,
    MessageDTO,
    RuntimeEventDTO,
    SessionDetailDTO,
    SessionListItemDTO,
)
from .serializers import (
    child_run_detail_dto,
    child_run_list_item_dto,
    context_state_dto,
    export_path_for_frontend,
    message_dtos,
    session_event_dtos,
    session_detail_dto,
    session_list_item_dto,
)
from langgraph_agent_blueprint.utils.ids import RUNTIME_ID_PATTERN

router = APIRouter()


@router.get("/sessions", response_model=list[SessionListItemDTO])
def list_sessions(request: Request) -> list[SessionListItemDTO]:
    runtime = request.app.state.runtime
    deps = runtime.dependencies
    project_root = _active_project_root(runtime)
    items: list[SessionListItemDTO] = []
    for metadata in deps.session_service.list(project_root):
        snapshot = None
        child_run_count = 0
        session_id = metadata.get("session_id")
        if session_id and project_root is not None:
            try:
                snapshot = deps.session_storage.load_session(project_root, session_id)
                child_run_count = len(deps.session_storage.list_child_runs(project_root, session_id))
            except (FileNotFoundError, OSError, ValueError):
                snapshot = None
        items.append(session_list_item_dto(metadata, snapshot, child_run_count=child_run_count))
    return items


@router.get("/sessions/{session_id}/events", response_model=list[RuntimeEventDTO])
def get_session_events(session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)], request: Request) -> list[RuntimeEventDTO]:
    runtime = request.app.state.runtime
    snapshot = runtime.dependencies.session_storage.load_session(_active_project_root(runtime), session_id)
    return session_event_dtos(snapshot, redactor=runtime.dependencies.observability_service.redact_payload)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageDTO])
def get_session_messages(session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)], request: Request) -> list[MessageDTO]:
    runtime = request.app.state.runtime
    snapshot = runtime.dependencies.session_storage.load_session(_active_project_root(runtime), session_id)
    return message_dtos(snapshot.get("messages", []))


@router.get("/sessions/{session_id}/context", response_model=ContextStateDTO)
def get_session_context(session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)], request: Request) -> ContextStateDTO:
    runtime = request.app.state.runtime
    snapshot = runtime.dependencies.session_storage.load_session(_active_project_root(runtime), session_id)
    return context_state_dto(snapshot, redactor=runtime.dependencies.observability_service.redact_payload)


@router.get("/sessions/{session_id}/child-runs", response_model=list[ChildRunListItemDTO])
def list_child_runs(session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)], request: Request) -> list[ChildRunListItemDTO]:
    runtime = request.app.state.runtime
    records = runtime.dependencies.session_storage.list_child_runs(_active_project_root(runtime), session_id)
    return [child_run_list_item_dto(record["metadata"], record.get("result", {})) for record in records]


@router.get("/sessions/{session_id}/child-runs/{child_run_id}", response_model=ChildRunDetailDTO)
def get_child_run(
    session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)],
    child_run_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)],
    request: Request,
) -> ChildRunDetailDTO:
    runtime = request.app.state.runtime
    record = runtime.dependencies.session_storage.load_child_run(_active_project_root(runtime), session_id, child_run_id)
    return child_run_detail_dto(record, redactor=runtime.dependencies.observability_service.redact_payload)


@router.post("/sessions/{session_id}/export", response_model=ExportRecordDTO)
def export_session(
    session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)],
    request_body: ExportRequest,
    request: Request,
) -> ExportRecordDTO:
    runtime = request.app.state.runtime
    deps = runtime.dependencies
    snapshot = deps.session_storage.load_session(_active_project_root(runtime), session_id)
    result = deps.export_service.export_transcript(session_id, snapshot.get("messages", []), request_body.format)
    return ExportRecordDTO(
        session_id=session_id,
        format=request_body.format,
        path=export_path_for_frontend(result.path, deps.config.storage_dir),
        bytes=len(result.text.encode("utf-8")),
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailDTO)
def get_session(session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)], request: Request) -> SessionDetailDTO:
    runtime = request.app.state.runtime
    project_root = _active_project_root(runtime)
    snapshot = runtime.dependencies.session_storage.load_session(project_root, session_id)
    child_records = runtime.dependencies.session_storage.list_child_runs(project_root, session_id)
    child_runs = [child_run_list_item_dto(record["metadata"], record.get("result", {})) for record in child_records]
    return session_detail_dto(snapshot, child_runs=child_runs, redactor=runtime.dependencies.observability_service.redact_payload)


def _active_project_root(runtime: object) -> str:
    deps = runtime.dependencies
    active = deps.workspace_service.get_active_workspace()
    if active is not None:
        return active.root_path
    return str(deps.config.project_root)
