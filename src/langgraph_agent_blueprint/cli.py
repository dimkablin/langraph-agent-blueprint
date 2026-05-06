"""Typer-based CLI adapter that sends interactive and headless requests into the shared LangGraph runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime

app = typer.Typer(help="LangGraph Agent Blueprint CLI")
sessions_app = typer.Typer(help="Session commands")
skills_app = typer.Typer(help="Skill commands")
tools_app = typer.Typer(help="Tool commands")
plugins_app = typer.Typer(help="Plugin commands")
app.add_typer(sessions_app, name="sessions")
app.add_typer(skills_app, name="skills")
app.add_typer(tools_app, name="tools")
app.add_typer(plugins_app, name="plugins")
console = Console()


def _runtime(project_root: Optional[Path] = None) -> AssistantGraphRuntime:
    config = AppConfig.from_env(project_root=project_root or Path.cwd())
    return AssistantGraphRuntime(build_dependencies(config))


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
    console.print("lg-agent chat. Type /exit to quit.")
    while True:
        try:
            message = console.input("> ")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if message.strip() in {"/exit", "exit", "quit"}:
            break
        result = runtime.invoke(message, input_kind="interactive")
        if "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            answer = console.input(f"Approve {payload.get('tool_name')}? [y/N] ")
            resumed = runtime.resume(result["thread_id"], {"approved": answer.strip().lower() in {"y", "yes"}})
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
    loaded = runtime.dependencies.session_service.resume(Path.cwd(), session_id)
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


@app.command()
def doctor() -> None:
    runtime = _runtime()
    console.print(json.dumps(runtime.dependencies.diagnostics_service.run(), indent=2))


def main() -> None:
    app()
