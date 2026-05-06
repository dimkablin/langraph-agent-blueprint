"""CLI chat observability session grouping tests."""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_blueprint import cli
from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.observability import LangfuseConfig
from langgraph_agent_blueprint.services.observability_service import ObservabilityService

from tests.test_observability_service import RecordingLangfuseFactory


def test_cli_chat_reuses_session_id_for_interactive_turns(monkeypatch, tmp_path: Path) -> None:
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
    messages = iter(["привет", "что ты умеешь?", "/exit"])

    monkeypatch.setattr(cli, "_runtime", lambda project_root=None: runtime)
    monkeypatch.setattr(cli.console, "input", lambda prompt="": next(messages))
    monkeypatch.setattr(cli.console, "print", lambda *args, **kwargs: None)

    cli.chat()

    traces = factory.client.top_level_traces
    assert len(traces) == 2
    assert traces[0]["session_id"] == traces[1]["session_id"]
    assert [trace["metadata"]["turn_index"] for trace in traces] == [1, 2]
    assert factory.client.unscoped_events == []
    assert all(observation["trace_id"] in {trace["trace_id"] for trace in traces} for observation in factory.client.child_observations)
