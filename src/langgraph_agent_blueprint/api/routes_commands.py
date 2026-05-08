"""FastAPI routes exposing registered slash command metadata."""

from fastapi import APIRouter, Request

from .schemas import CommandRegistryDTO

router = APIRouter()


@router.get("/commands", response_model=CommandRegistryDTO)
def list_commands(request: Request) -> dict:
    return request.app.state.runtime.dependencies.command_registry.snapshot()
