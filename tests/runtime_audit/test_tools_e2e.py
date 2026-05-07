"""Runtime-audit regression tests proving end-to-end graph behavior for commands, skills, providers, and tools."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def _runtime(tmp_path, **overrides):
    config = AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake", **overrides)
    return AssistantGraphRuntime(build_dependencies(config))


def test_edit_file_uses_prior_read_from_persisted_session(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("old", encoding="utf-8")
    runtime = _runtime(tmp_path)

    runtime.invoke('tool:read_file {"path":"a.txt"}', input_kind="headless", project_root=tmp_path, session_id="s1")
    first = runtime.invoke(
        'tool:edit_file {"path":"a.txt","old_text":"old","new_text":"new"}',
        input_kind="headless",
        project_root=tmp_path,
        session_id="s1",
        thread_id="edit-file",
    )
    assert "__interrupt__" in first

    result = runtime.resume("edit-file", {"approved": True})

    assert target.read_text(encoding="utf-8") == "new"
    assert any(isinstance(item, dict) and item.get("approved") is True for item in result["permission_decisions"])
    assert any(event["type"] == "tool_call_finished" for event in result["ui_events"])


def test_write_file_accepts_json_fake_tool_arguments(tmp_path):
    runtime = _runtime(tmp_path)

    first = runtime.invoke(
        'tool:write_file {"path":"created.txt","content":"hello"}',
        input_kind="headless",
        project_root=tmp_path,
        thread_id="write-json",
    )
    assert "__interrupt__" in first

    result = runtime.resume("write-json", {"approved": True})

    assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "hello"
    assert result["tool_results"][-1]["status"] == "ok"


def test_notebook_edit_runs_after_permission_approval(tmp_path):
    notebook = {
        "cells": [{"cell_type": "code", "source": ["print('old')\n"], "metadata": {}, "outputs": [], "execution_count": None}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (tmp_path / "notebook.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    runtime = _runtime(tmp_path)

    first = runtime.invoke(
        'tool:notebook_edit {"path":"notebook.ipynb","index":0,"source":"print(\\"hello\\")"}',
        input_kind="headless",
        project_root=tmp_path,
        thread_id="notebook-edit",
    )
    assert "__interrupt__" in first

    runtime.resume("notebook-edit", {"approved": True})

    updated = json.loads((tmp_path / "notebook.ipynb").read_text(encoding="utf-8"))
    assert updated["cells"][0]["source"] == ['print("hello")']


def test_web_search_without_provider_is_unavailable_after_approval(tmp_path):
    runtime = _runtime(tmp_path, network_enabled=True)

    first = runtime.invoke('tool:web_search {"query":"weather"}', input_kind="headless", project_root=tmp_path, thread_id="web-search")
    assert "__interrupt__" in first
    assert first["pending_confirmation"]["tool_name"] == "web_search"

    result = runtime.resume("web-search", {"approved": True})

    assert result["tool_results"][-1]["status"] == "error"
    assert "provider is not configured" in result["tool_results"][-1]["content"]


def test_web_fetch_enabled_marks_content_untrusted_after_approval(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"local web acceptance")

        def log_message(self, format, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    runtime = _runtime(tmp_path, network_enabled=True, web_fetch_allow_private_hosts=True)
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        first = runtime.invoke(f'tool:web_fetch {{"url":"{url}"}}', input_kind="headless", project_root=tmp_path, thread_id="web-fetch")
        assert "__interrupt__" in first

        result = runtime.resume("web-fetch", {"approved": True})
    finally:
        server.shutdown()
        server.server_close()

    assert "local web acceptance" in result["final_response"]
    assert "untrusted" in result["tool_results"][-1]["metadata"]["warning"].lower()


def test_powershell_runs_after_permission_approval_on_windows(tmp_path):
    runtime = _runtime(tmp_path)

    first = runtime.invoke(
        'tool:powershell {"command":"Write-Output smoke-powershell"}',
        input_kind="headless",
        project_root=tmp_path,
        thread_id="powershell",
    )
    assert "__interrupt__" in first

    result = runtime.resume("powershell", {"approved": True})

    assert "smoke-powershell" in result["final_response"]


def test_grep_relative_path_is_resolved_under_project_root(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "math_utils.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    runtime = _runtime(tmp_path)

    result = runtime.invoke('tool:grep {"pattern":"def add","path":"src"}', input_kind="headless", project_root=tmp_path)

    assert "def add" in result["final_response"]


def test_bash_accepts_json_fake_tool_arguments_after_approval(tmp_path):
    runtime = _runtime(tmp_path)

    first = runtime.invoke('tool:bash {"command":"echo smoke-bash"}', input_kind="headless", project_root=tmp_path, thread_id="bash-json")
    assert "__interrupt__" in first

    result = runtime.resume("bash-json", {"approved": True})

    assert "smoke-bash" in result["final_response"]
