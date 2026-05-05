from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/commands")
def list_commands(request: Request) -> dict:
    return request.app.state.runtime.dependencies.command_registry.snapshot()
