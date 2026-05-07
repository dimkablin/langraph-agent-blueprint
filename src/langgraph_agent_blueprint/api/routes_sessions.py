"""FastAPI session routes for listing and loading persisted graph sessions."""

from typing import Annotated

from fastapi import APIRouter, Path, Request

from langgraph_agent_blueprint.utils.ids import RUNTIME_ID_PATTERN

router = APIRouter()


@router.get("/sessions")
def list_sessions(request: Request) -> list[dict]:
    runtime = request.app.state.runtime
    return runtime.dependencies.session_service.list()


@router.get("/sessions/{session_id}")
def get_session(session_id: Annotated[str, Path(pattern=RUNTIME_ID_PATTERN)], request: Request) -> dict:
    runtime = request.app.state.runtime
    return runtime.dependencies.session_storage.load_session(runtime.dependencies.config.project_root, session_id)
