"""Typer-based CLI adapter that sends interactive and headless requests into the shared LangGraph runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from langgraph_agent_blueprint.config import AppConfig, format_config_explain, format_config_show, format_config_validate
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.evals.loader import load_scenario_by_id, load_scenarios
from langgraph_agent_blueprint.evals.runner import EvalRunner
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.utils.ids import new_id, validate_session_id

app = typer.Typer(help="LangGraph Agent Blueprint CLI")
sessions_app = typer.Typer(help="Session commands")
skills_app = typer.Typer(help="Skill commands")
tools_app = typer.Typer(help="Tool commands")
plugins_app = typer.Typer(help="Plugin commands")
eval_app = typer.Typer(help="Eval/replay commands")
config_app = typer.Typer(help="Config diagnostics commands")
app.add_typer(sessions_app, name="sessions")
app.add_typer(skills_app, name="skills")
app.add_typer(tools_app, name="tools")
app.add_typer(plugins_app, name="plugins")
app.add_typer(eval_app, name="eval")
app.add_typer(config_app, name="config")
console = Console()


def _runtime(project_root: Optional[Path] = None) -> AssistantGraphRuntime:
    config = AppConfig.from_env(project_root=project_root or Path.cwd())
    return AssistantGraphRuntime(build_dependencies(config))


def _config_report(project_root: Optional[Path] = None) -> AppConfig:
    config, _report = AppConfig.load_with_report(project_root=project_root or Path.cwd())
    return config


@app.command()
def query(
    message: str,
    output: str = typer.Option("text", "--output", "-o", help="text, json, or stream-json"),
) -> None:
    """Run a non-interactive query through the main graph."""

    runtime = _runtime()
    if output == "stream-json":
        for event in runtime.stream(message, input_kind="headless"):
            print(json.dumps(event, ensure_ascii=False))
        return
    result = runtime.invoke(message, input_kind="headless")
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        if output == "json":
            print(json.dumps({"permission_required": payload, "session_id": result["session_id"]}, ensure_ascii=False))
        else:
            console.print(f"Permission required for {payload.get('tool_name')}: {payload.get('reason')}")
        return
    if output == "json":
        print(json.dumps({"session_id": result["session_id"], "final_response": result["final_response"], "usage": result.get("usage", {})}, ensure_ascii=False))
    else:
        console.print(result["final_response"])


@app.command()
def chat() -> None:
    """Start an interactive terminal chat adapter."""

    runtime = _runtime()
    session_id = new_id("session")
    turn_index = 0
    console.print("lg-agent chat. Type /exit to quit.")
    while True:
        try:
            message = console.input("> ")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if message.strip() in {"/exit", "exit", "quit"}:
            break
        turn_index += 1
        result = runtime.invoke(message, input_kind="interactive", session_id=session_id, turn_index=turn_index)
        if "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            answer = console.input(f"Approve {payload.get('tool_name')}? [y/N] ")
            resumed = runtime.resume(
                result["thread_id"],
                {"approved": answer.strip().lower() in {"y", "yes"}},
                session_id=result.get("session_id"),
            )
            console.print(resumed.get("final_response", ""))
        else:
            console.print(result.get("final_response", ""))


@sessions_app.command("list")
def list_sessions() -> None:
    runtime = _runtime()
    console.print(json.dumps(runtime.dependencies.session_service.list(Path.cwd()), indent=2, default=str))


@sessions_app.command("resume")
def resume_session(session_id: str) -> None:
    runtime = _runtime()
    try:
        session_id = validate_session_id(session_id)
        loaded = runtime.dependencies.session_service.resume(Path.cwd(), session_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="session_id") from exc
    console.print(f"Loaded {loaded['metadata']['session_id']} with {len(loaded['messages'])} messages")


@skills_app.command("list")
def list_skills() -> None:
    runtime = _runtime()
    for name, meta in runtime.dependencies.skill_registry.snapshot().items():
        console.print(f"{name}: {meta.get('description', '')}")


@tools_app.command("list")
def list_tools() -> None:
    runtime = _runtime()
    for name, meta in runtime.dependencies.tool_registry.snapshot().items():
        console.print(f"{name}: {meta.get('description', '')}")


@plugins_app.command("list")
def list_plugins() -> None:
    runtime = _runtime()
    console.print(json.dumps(runtime.dependencies.plugin_service.discover(), indent=2, ensure_ascii=False))


@plugins_app.command("install")
def install_plugin(source: str) -> None:
    runtime = _runtime()
    result = runtime.dependencies.plugin_service.install(source)
    console.print(result.model_dump_json(indent=2))


@plugins_app.command("update")
def update_plugin(name: str) -> None:
    runtime = _runtime()
    result = runtime.dependencies.plugin_service.update(name)
    console.print(result.model_dump_json(indent=2))


@plugins_app.command("remove")
def remove_plugin(name: str) -> None:
    runtime = _runtime()
    result = runtime.dependencies.plugin_service.remove(name)
    console.print(result.model_dump_json(indent=2))


@eval_app.command("list")
def list_evals(
    scenarios_dir: Optional[Path] = typer.Option(None, "--scenarios-dir", help="Directory containing eval scenario YAML/JSON files."),
) -> None:
    """List available eval/replay scenarios."""

    for scenario in load_scenarios(scenarios_dir):
        console.print(f"{scenario.id}: {scenario.description}")


@eval_app.command("run")
def run_eval(
    scenario_id: Optional[str] = typer.Argument(None, help="Scenario id to run."),
    run_all: bool = typer.Option(False, "--all", help="Run all scenarios."),
    report_dir: Path = typer.Option(Path(".eval_runs"), "--report-dir", help="Directory where eval reports are written."),
    scenarios_dir: Optional[Path] = typer.Option(None, "--scenarios-dir", help="Directory containing eval scenario YAML/JSON files."),
) -> None:
    """Run one or all eval/replay scenarios through the graph runtime."""

    if not run_all and not scenario_id:
        raise typer.BadParameter("Provide a scenario id or --all")
    runner = EvalRunner(report_root=report_dir)
    scenarios = load_scenarios(scenarios_dir) if run_all else [load_scenario_by_id(str(scenario_id), scenarios_dir)]
    failed = False
    for scenario in scenarios:
        result = runner.run_scenario(scenario)
        status = "passed" if result.passed else "failed"
        console.print(f"{result.scenario_id}: {status}")
        for failure in result.failures:
            console.print(f"  - {failure}")
        console.print(f"  report: {result.metadata.get('report_json')}")
        failed = failed or not result.passed
    if failed:
        raise typer.Exit(code=1)


@config_app.command("show")
def config_show() -> None:
    """Show the redacted effective runtime config."""

    console.print(format_config_show(_config_report()))


@config_app.command("explain")
def config_explain() -> None:
    """Show config sources and value origins."""

    config = _config_report()
    console.print(format_config_explain(config.config_report))


@config_app.command("validate")
def config_validate() -> None:
    """Validate config and print structured diagnostics."""

    config = _config_report()
    console.print(format_config_validate(config.config_report))


@app.command()
def doctor() -> None:
    runtime = _runtime()
    diagnostics = runtime.dependencies.diagnostics_service.run()
    diagnostics["mcp"] = runtime.dependencies.mcp_service.diagnostics()
    diagnostics["langfuse"] = runtime.dependencies.observability_service.status()
    console.print(json.dumps(diagnostics, indent=2))


def main() -> None:
    app()
