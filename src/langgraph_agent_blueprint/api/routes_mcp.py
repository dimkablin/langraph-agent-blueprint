"""FastAPI routes exposing MCP discovery status and metadata."""

from fastapi import APIRouter, Request

from .schemas import MCPStatusDTO

router = APIRouter()


@router.get("/mcp", response_model=MCPStatusDTO)
def list_mcp(request: Request) -> dict:
    return request.app.state.runtime.dependencies.mcp_service.discover()
