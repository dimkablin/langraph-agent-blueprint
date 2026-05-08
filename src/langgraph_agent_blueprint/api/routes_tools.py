"""FastAPI routes exposing registered model-callable tool metadata."""

from fastapi import APIRouter, Request

from .schemas import ToolRegistryDTO

router = APIRouter()


@router.get("/tools", response_model=ToolRegistryDTO)
def list_tools(request: Request) -> dict:
    return request.app.state.runtime.dependencies.tool_registry.snapshot()
