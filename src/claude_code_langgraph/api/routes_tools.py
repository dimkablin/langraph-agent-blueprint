"""FastAPI routes exposing registered model-callable tool metadata."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/tools")
def list_tools(request: Request) -> dict:
    return request.app.state.runtime.dependencies.tool_registry.snapshot()
