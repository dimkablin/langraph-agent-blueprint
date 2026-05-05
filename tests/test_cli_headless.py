import json
import os
import subprocess
import sys


def run_cli(tmp_path, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["LLM_PROVIDER"] = "fake"
    env["CC_LANGGRAPH_STORAGE_DIR"] = str(tmp_path)
    return subprocess.run(
        [sys.executable, "-m", "claude_code_langgraph", *args],
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
