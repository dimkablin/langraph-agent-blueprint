"""OpenAPI DTO contract coverage for future typed frontend clients."""

from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def test_openapi_exposes_frontend_contract_dtos(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    schemas = app.openapi()["components"]["schemas"]

    expected = {
        "RuntimeEventDTO",
        "StreamFrame",
        "PermissionDecisionDTO",
        "ApprovalRequest",
        "ChatRequest",
        "ChatResponse",
        "SessionListItemDTO",
        "SessionDetailDTO",
        "MessageDTO",
        "ToolCallRecordDTO",
        "ChildRunListItemDTO",
        "ChildRunDetailDTO",
        "ContextStateDTO",
        "ConfigShowDTO",
        "ConfigExplainDTO",
        "ConfigValidateDTO",
        "PluginStatusDTO",
        "HookStatusDTO",
        "MCPStatusDTO",
        "ObservabilityStatusDTO",
    }

    assert expected <= set(schemas)


def test_chat_response_events_use_runtime_event_dto(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    chat_response_schema = app.openapi()["components"]["schemas"]["ChatResponse"]

    event_items = chat_response_schema["properties"]["events"]["items"]
    assert event_items == {"$ref": "#/components/schemas/RuntimeEventDTO"}


def test_chat_request_exposes_typed_model_intelligence_contract(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    chat_request_schema = app.openapi()["components"]["schemas"]["ChatRequest"]

    model_intelligence = chat_request_schema["properties"]["model_intelligence"]
    assert model_intelligence["anyOf"][0]["enum"] == ["low", "medium", "high", "very_high"]


def test_registry_endpoints_return_typed_object_maps(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    for path in ["/commands", "/skills", "/tools"]:
        payload = client.get(path).json()
        assert isinstance(payload, dict)
        assert payload
        first = next(iter(payload.values()))
        assert "name" in first
        assert "description" in first
