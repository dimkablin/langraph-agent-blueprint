"""Eval/replay runner that executes scenarios through AssistantGraphRuntime."""

from __future__ import annotations

import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.evals.assertions import EvalAssertionEngine
from langgraph_agent_blueprint.evals.loader import default_fixtures_dir, repo_root
from langgraph_agent_blueprint.evals.reporter import EvalReporter
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.evals import EvalReport, EvalRunResult, EvalScenario
from langgraph_agent_blueprint.models.observability import LangfuseConfig
from langgraph_agent_blueprint.utils.ids import new_id


class EvalRunner:
    """Run validated eval scenarios against the real LangGraph runtime."""

    def __init__(
        self,
        *,
        report_root: str | Path | None = None,
        fixtures_root: str | Path | None = None,
        workspace_root: str | Path | None = None,
        assertion_engine: EvalAssertionEngine | None = None,
        reporter: EvalReporter | None = None,
    ) -> None:
        self.report_root = Path(report_root) if report_root is not None else Path(".eval_runs")
        self.fixtures_root = Path(fixtures_root) if fixtures_root is not None else default_fixtures_dir()
        self.workspace_root = Path(workspace_root) if workspace_root is not None else None
        self.assertion_engine = assertion_engine or EvalAssertionEngine()
        self.reporter = reporter or EvalReporter()

    def run_scenario(self, scenario: EvalScenario) -> EvalRunResult:
        """Execute one scenario and write a report."""

        started = time.perf_counter()
        run_id = new_id("eval")
        run_dir = self._run_dir(run_id, scenario.id)
        run_dir.mkdir(parents=True, exist_ok=True)
        workspace = self._prepare_workspace(scenario, run_dir)
        storage_dir = run_dir / "storage"
        config = self._config_for_scenario(scenario, workspace, storage_dir)
        deps = build_dependencies(config)
        runtime = AssistantGraphRuntime(deps)
        session_id = new_id("session")
        events: list[dict[str, Any]] = []
        failures: list[str] = []
        final_state: dict[str, Any] = {}
        try:
            for index, step in enumerate(scenario.steps):
                result = runtime.invoke(
                    step.input.text,
                    input_kind="headless",
                    session_id=session_id,
                    project_root=workspace,
                    turn_index=index + 1,
                )
                result_events = _events(result)
                events.extend(result_events)
                if "__interrupt__" in result and step.input.approve is not None:
                    decision = dict(step.input.resume_payload or {})
                    decision.setdefault("approved", step.input.approve)
                    result = runtime.resume(result["thread_id"], decision, session_id=result.get("session_id", session_id))
                    result_events = _events(result)
                    events.extend(result_events)
                elif "__interrupt__" in result:
                    failures.append(f"Step {index + 1} interrupted but no approval decision was provided")
                step_state = dict(result)
                step_state["ui_events"] = result_events
                failures.extend(
                    f"Step {index + 1}: {failure}"
                    for failure in self.assertion_engine.assert_expectations(step_state, step.expect, workspace=workspace)
                )
                final_state = result if isinstance(result, dict) else {}
        except Exception as exc:
            failures.append(f"Scenario execution failed: {exc.__class__.__name__}: {exc}")
        finally:
            deps.mcp_service.close()
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        result = EvalRunResult(
            scenario_id=scenario.id,
            passed=not failures,
            failures=failures,
            events=events,
            final_state=final_state,
            metadata={
                "run_id": run_id,
                "duration_ms": duration_ms,
                "provider": config.llm_provider,
                "workspace": str(workspace),
                "storage_dir": str(storage_dir),
                "workspace_fixture": scenario.workspace_fixture,
                "mcp_fixture": scenario.mcp_fixture,
                "plugin_fixtures": list(scenario.plugin_fixtures),
                "run_dir": str(run_dir),
            },
        )
        scenario_json, scenario_md = self.reporter.write_scenario_result(run_dir, result)
        result.metadata["report_json"] = str(scenario_json)
        result.metadata["report_md"] = str(scenario_md)
        report = EvalReport(run_id=run_id, passed=result.passed, results=[result], metadata={"run_dir": str(run_dir)})
        report_json, report_md = self.reporter.write_run_report(run_dir, report)
        result.metadata["run_report_json"] = str(report_json)
        result.metadata["run_report_md"] = str(report_md)
        self.reporter.write_scenario_result(run_dir, result)
        self.reporter.write_run_report(run_dir, report)
        return result

    def _run_dir(self, run_id: str, scenario_id: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_scenario = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in scenario_id)[:80]
        return self.report_root / f"{stamp}-{safe_scenario}-{run_id}"

    def _prepare_workspace(self, scenario: EvalScenario, run_dir: Path) -> Path:
        if self.workspace_root is not None:
            return self.workspace_root.resolve()
        workspace = run_dir / "workspace"
        if scenario.workspace_fixture:
            source = (self.fixtures_root / "workspaces" / scenario.workspace_fixture).resolve()
            if not source.is_dir():
                raise FileNotFoundError(f"Workspace fixture not found: {scenario.workspace_fixture}")
            shutil.copytree(source, workspace)
        else:
            workspace.mkdir(parents=True, exist_ok=True)
        return workspace.resolve()

    def _config_for_scenario(self, scenario: EvalScenario, workspace: Path, storage_dir: Path) -> AppConfig:
        plugin_paths = [self._plugin_fixture_path(name) for name in scenario.plugin_fixtures]
        return AppConfig(
            llm_provider=scenario.provider,  # type: ignore[arg-type]
            model_name="fake-model",
            storage_dir=storage_dir,
            project_root=workspace,
            cwd=workspace,
            network_enabled=False,
            plugin_paths=plugin_paths,
            mcp_config=self._mcp_config(scenario),
            langfuse=LangfuseConfig(enabled=False, environment="eval"),
        )

    def _plugin_fixture_path(self, fixture_name: str) -> Path:
        path = (self.fixtures_root / "plugins" / fixture_name).resolve()
        if not path.is_dir():
            example_path = (repo_root() / "examples" / "plugins" / fixture_name).resolve()
            if example_path.is_dir():
                return example_path
            raise FileNotFoundError(f"Plugin fixture not found: {fixture_name}")
        return path

    def _mcp_config(self, scenario: EvalScenario) -> dict[str, Any]:
        if not scenario.mcp_fixture:
            return {}
        if scenario.mcp_fixture != "fake_stdio":
            raise ValueError(f"Unsupported MCP fixture: {scenario.mcp_fixture}")
        server_path = repo_root() / "tests" / "fixtures" / "mcp" / "fake_mcp_server.py"
        return {
            "servers": {
                "fake": {
                    "enabled": True,
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [str(server_path)],
                    "timeout_seconds": 5,
                }
            }
        }


def _events(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    return [item for item in result.get("ui_events", []) if isinstance(item, dict)]
