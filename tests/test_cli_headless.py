"""Pytest coverage for cli headless behavior in the Python/LangGraph assistant."""

import json
import os
import subprocess
import sys
import types

from typer.testing import CliRunner

from langgraph_agent_blueprint import cli


def run_cli(tmp_path, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["LLM_PROVIDER"] = "fake"
    env["CC_LANGGRAPH_STORAGE_DIR"] = str(tmp_path)
    return subprocess.run(
        [sys.executable, "-m", "langgraph_agent_blueprint", *args],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def test_headless_query_text_output_uses_graph(tmp_path):
    result = run_cli(tmp_path, "query", "--output", "text", "hello")
    assert "Fake response: hello" in result.stdout


def test_headless_query_json_output_uses_graph(tmp_path):
    result = run_cli(tmp_path, "query", "--output", "json", "hello")
    payload = json.loads(result.stdout)
    assert payload["final_response"] == "Fake response: hello"
    assert payload["session_id"]


def test_headless_stream_json_outputs_runtime_events(tmp_path):
    result = run_cli(tmp_path, "query", "--output", "stream-json", 'tool:read_file {"path":"README.md"}')
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    event_types = [event["type"] for event in events]

    assert len(events) > 3
    assert "tool_call_started" in event_types
    assert "tool_call_finished" in event_types
    assert event_types[-1] == "final_response"


def test_serve_command_delegates_to_uvicorn_with_runtime_api(monkeypatch):
    calls = []

    def fake_run_api_server(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(cli, "_run_api_server", fake_run_api_server)

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--factory", "--host", "127.0.0.1", "--port", "8000", "--reload"],
    )

    assert result.exit_code == 0
    assert calls == [
        {
            "app_path": "langgraph_agent_blueprint.api.server:create_app",
            "factory": True,
            "host": "127.0.0.1",
            "port": 8000,
            "reload": True,
        }
    ]


def test_run_api_server_forwards_uvicorn_options(monkeypatch):
    calls = []

    def fake_uvicorn_run(app_path, **kwargs):
        calls.append((app_path, kwargs))

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=fake_uvicorn_run))

    cli._run_api_server(
        app_path="langgraph_agent_blueprint.api.server:create_app",
        factory=True,
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_level="debug",
    )

    assert calls == [
        (
            "langgraph_agent_blueprint.api.server:create_app",
            {
                "factory": True,
                "host": "0.0.0.0",
                "port": 9000,
                "reload": True,
                "log_level": "debug",
            },
        )
    ]
