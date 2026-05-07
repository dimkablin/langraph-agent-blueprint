"""Observability regression tests for subagent events."""

from __future__ import annotations

import json
from pathlib import Path

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.observability import LangfuseConfig
from langgraph_agent_blueprint.services.observability_service import ObservabilityService

from tests.test_observability_service import RecordingLangfuseFactory


def test_subagent_runtime_events_are_scoped_to_parent_trace(tmp_path: Path) -> None:
    factory = RecordingLangfuseFactory()
    deps = build_dependencies(
        AppConfig(
            storage_dir=tmp_path / "storage",
            project_root=tmp_path,
            cwd=tmp_path,
            llm_provider="fake",
            langfuse=LangfuseConfig(
                enabled=True,
                public_key="pk",
                secret_key="sk",
                base_url="https://langfuse.example",
                environment="ci",
            ),
        )
    )
    deps.observability_service = ObservabilityService(deps.config.langfuse, factory=factory)
    runtime = AssistantGraphRuntime(deps)
    prompt = json.dumps({"prompt": "hello from child", "name": "observer"})

    result = runtime.invoke(f"tool:agent {prompt}", input_kind="headless", project_root=tmp_path)

    names = [event["name"] for event in factory.client.child_observations]
    assert result["child_runs"]
    assert "runtime.subagent_started" in names
    assert "runtime.subagent_finished" in names
    assert factory.client.unscoped_events == []

