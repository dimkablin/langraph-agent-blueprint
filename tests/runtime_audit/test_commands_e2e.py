"""Runtime-audit regression tests proving end-to-end graph behavior for commands, skills, providers, and tools."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime


def _runtime(tmp_path):
    return AssistantGraphRuntime(
        build_dependencies(AppConfig(storage_dir=tmp_path / "storage", project_root=tmp_path, cwd=tmp_path, llm_provider="fake"))
    )


def test_compact_command_runs_compaction_path(tmp_path):
    result = _runtime(tmp_path).invoke("/compact", input_kind="headless", project_root=tmp_path)

    assert result["final_response"] == "Context compacted."
    assert any(event["type"] == "compact_finished" for event in result["ui_events"])
    assert result["context_status"]["compacted"] is True


def test_clear_command_clears_message_history(tmp_path):
    runtime = _runtime(tmp_path)
    result = runtime.invoke("/clear", input_kind="headless", project_root=tmp_path)

    assert result["final_response"] == "Conversation cleared."
    assert result["messages"] == []


def test_cost_command_reports_unavailable_cost_without_error(tmp_path):
    result = _runtime(tmp_path).invoke("/cost", input_kind="headless", project_root=tmp_path)

    assert "Usage:" in result["final_response"]
    assert "Cost: unavailable" in result["final_response"]


def test_export_command_creates_transcript_file(tmp_path):
    runtime = _runtime(tmp_path)

    result = runtime.invoke("/export", input_kind="headless", project_root=tmp_path)

    assert result["exported_outputs"]
    export_path = Path(result["exported_outputs"][0]["path"])
    assert export_path.exists()
    assert "Exported transcript" in result["final_response"]


def test_doctor_command_runs_diagnostics_service(tmp_path):
    result = _runtime(tmp_path).invoke("/doctor", input_kind="headless", project_root=tmp_path)

    assert '"status": "ok"' in result["final_response"]
    assert "diagnostics" in result["metadata"]


def test_status_command_reports_workspace_not_storage(tmp_path):
    result = _runtime(tmp_path).invoke("/status", input_kind="headless", project_root=tmp_path)

    assert f"project_root: {tmp_path}" in result["final_response"]
    assert f"storage_dir: {tmp_path / 'storage'}" in result["final_response"]
    assert str(tmp_path / "storage") != result["project_root"]


def test_todo_write_persists_to_later_todo_command(tmp_path):
    runtime = _runtime(tmp_path)
    session_id = "todo-session"

    runtime.invoke(
        'tool:todo_write {"todos":[{"id":"1","content":"audit","status":"in_progress"}]}',
        input_kind="headless",
        project_root=tmp_path,
        session_id=session_id,
    )
    result = runtime.invoke("/todo", input_kind="headless", project_root=tmp_path, session_id=session_id)

    assert "audit" in result["final_response"]


def test_resume_command_restores_named_session_state(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.invoke(
        'tool:todo_write {"todos":[{"id":"1","content":"resume me","status":"done"}]}',
        input_kind="headless",
        project_root=tmp_path,
        session_id="resume-source",
    )

    result = runtime.invoke("/resume resume-source", input_kind="headless", project_root=tmp_path)

    assert result["session_id"] == "resume-source"
    assert result["todos"][0]["content"] == "resume me"
    assert "Resumed session: resume-source" == result["final_response"]


def test_remember_skill_persists_to_memory_command(tmp_path):
    runtime = _runtime(tmp_path)

    runtime.invoke("/skill remember project: Prefer pytest.", input_kind="headless", project_root=tmp_path)
    result = runtime.invoke("/memory", input_kind="headless", project_root=tmp_path)

    assert "Prefer pytest." in result["final_response"]
    assert any(event["type"] == "command_finished" for event in result["ui_events"])
