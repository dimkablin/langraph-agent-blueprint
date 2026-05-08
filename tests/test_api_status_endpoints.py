"""Read-only runtime status endpoint contract tests."""

from fastapi.testclient import TestClient

from langgraph_agent_blueprint.api.server import create_app
from langgraph_agent_blueprint.config import AppConfig


def test_read_only_runtime_status_endpoints(tmp_path):
    app = create_app(AppConfig(storage_dir=tmp_path, llm_provider="fake"))
    client = TestClient(app)

    plugins = client.get("/plugins")
    hooks = client.get("/hooks")
    config = client.get("/config")
    explain = client.get("/config/explain")
    validate = client.get("/config/validate")
    observability = client.get("/observability")
    mcp = client.get("/mcp")

    for response in [plugins, hooks, config, explain, validate, observability, mcp]:
        assert response.status_code == 200

    assert {"plugins", "errors", "warnings"} <= set(plugins.json())
    assert "hooks" in hooks.json()
    assert "values" in config.json()
    assert "sources" in explain.json()
    assert "diagnostics" in validate.json()
    assert {"enabled", "mode", "sdk_installed"} <= set(observability.json())
    assert {"servers", "tools", "resources", "prompts", "invalid_servers"} <= set(mcp.json())

