"""OpenAPI and router contract tests for frontend registry routes."""

from collections import Counter

from fastapi.routing import APIRoute

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def test_registry_routes_are_defined_once(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    routes = [
        (next(iter(route.methods - {"HEAD", "OPTIONS"})), route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
    ]
    counts = Counter(routes)

    assert counts[("GET", "/commands")] == 1
    assert counts[("GET", "/skills")] == 1
    assert counts[("GET", "/tools")] == 1


def test_openapi_exposes_registry_dtos_once(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    openapi = app.openapi()

    assert set(openapi["paths"]["/commands"]) == {"get"}
    assert set(openapi["paths"]["/skills"]) == {"get"}
    assert set(openapi["paths"]["/tools"]) == {"get"}
    schemas = openapi["components"]["schemas"]
    assert "CommandRegistryDTO" in schemas
    assert "SkillRegistryDTO" in schemas
    assert "ToolRegistryDTO" in schemas

