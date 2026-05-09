"""Read-only runtime status endpoint contract tests."""

import sys
from pathlib import Path

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


def test_mcp_snapshot_does_not_start_stdio_discovery(tmp_path):
    server = Path(__file__).parent / "fixtures" / "mcp" / "fake_mcp_server.py"
    app = create_app(
        AppConfig(
            storage_dir=tmp_path,
            llm_provider="fake",
            mcp_config={
                "servers": {
                    "fake": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [str(server)],
                    }
                }
            },
        )
    )
    client = TestClient(app)

    snapshot = client.get("/mcp/snapshot")

    assert snapshot.status_code == 200
    payload = snapshot.json()
    assert payload["servers"][0]["name"] == "fake"
    assert payload["servers"][0]["status"] == "configured"
    assert payload["tools"] == {}
    assert not any(event["type"] == "mcp_server_connected" for event in payload["events"])
    assert any("discovery has not been run" in str(warning).lower() for warning in payload["warnings"])

    discovered = client.get("/mcp")
    try:
        assert discovered.status_code == 200
        assert "mcp.fake.echo" in discovered.json()["tools"]
    finally:
        app.state.runtime.dependencies.mcp_service.close()
