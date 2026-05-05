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

