from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/mcp")
def list_mcp(request: Request) -> dict:
    return request.app.state.runtime.dependencies.mcp_service.discover()
