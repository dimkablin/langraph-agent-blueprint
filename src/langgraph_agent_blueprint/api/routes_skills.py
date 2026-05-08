"""FastAPI routes exposing loaded and disabled skill metadata."""

from fastapi import APIRouter, Request

from .schemas import SkillRegistryDTO

router = APIRouter()


@router.get("/skills", response_model=SkillRegistryDTO)
def list_skills(request: Request) -> dict:
    return request.app.state.runtime.dependencies.skill_registry.snapshot()
