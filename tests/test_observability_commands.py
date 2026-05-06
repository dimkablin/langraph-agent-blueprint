"""Slash command diagnostics coverage for observability."""

from __future__ import annotations

import json

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.observability import LangfuseConfig
from langgraph_agent_blueprint.services.observability_service import ObservabilityService

from tests.test_observability_service import RecordingLangfuseFactory


def _runtime(tmp_path) -> AssistantGraphRuntime:
    deps = build_dependencies(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            llm_provider="fake",
            langfuse=LangfuseConfig(
                enabled=True,
                public_key="pk-lf-test",
                secret_key="sk-lf-test",
                base_url="https://langfuse.example",
            ),
        )
    )
    deps.observability_service = ObservabilityService(deps.config.langfuse, factory=RecordingLangfuseFactory())
    return AssistantGraphRuntime(deps)


def test_doctor_includes_langfuse_status(tmp_path) -> None:
    runtime = _runtime(tmp_path)

    result = runtime.invoke("/doctor", input_kind="headless", project_root=tmp_path)
    diagnostics = json.loads(result["final_response"])

    assert diagnostics["langfuse"]["enabled"] is True
    assert diagnostics["langfuse"]["base_url_configured"] is True
    assert "sk-lf-test" not in result["final_response"]


def test_config_command_redacts_langfuse_keys(tmp_path) -> None:
    runtime = _runtime(tmp_path)

    result = runtime.invoke("/config", input_kind="headless", project_root=tmp_path)

    assert "pk-lf-test" not in result["final_response"]
    assert "sk-lf-test" not in result["final_response"]
    assert "'secret_key': '***'" in result["final_response"] or '"secret_key": "***"' in result["final_response"]


def test_observability_command_reports_status(tmp_path) -> None:
    runtime = _runtime(tmp_path)

    result = runtime.invoke("/observability", input_kind="headless", project_root=tmp_path)

    assert "Langfuse: enabled" in result["final_response"]
    assert "mode:" in result["final_response"]
    assert "sk-lf-test" not in result["final_response"]
