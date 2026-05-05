from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from claude_code_langgraph.utils.ids import new_id


class AssistantState(TypedDict, total=False):
    session_id: str
    thread_id: str
    project_root: str
    cwd: str
    input_text: str
    input_kind: Literal["interactive", "headless", "command", "resume", "approval"]
    messages: Annotated[list[BaseMessage], add_messages]
    attachments: list[dict[str, Any]]
    active_command: dict[str, Any] | None
    active_skill: dict[str, Any] | None
    available_tools: dict[str, dict[str, Any]]
    available_commands: dict[str, dict[str, Any]]
    available_skills: dict[str, dict[str, Any]]
    pending_tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    pending_confirmation: dict[str, Any] | None
    permissions: dict[str, Any]
    permission_decisions: list[dict[str, Any]]
    plan_mode: dict[str, Any]
    todos: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    memory: dict[str, Any]
    context_status: dict[str, Any]
    usage: dict[str, Any]
    mcp_state: dict[str, Any]
    plugin_state: dict[str, Any]
    hooks_state: dict[str, Any]
    child_runs: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    exported_outputs: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    ui_events: list[dict[str, Any]]
    final_response: str | None
    metadata: dict[str, Any]


def create_initial_state(
    input_text: str,
    project_root: str | Path | None = None,
    cwd: str | Path | None = None,
    input_kind: str = "headless",
    session_id: str | None = None,
    thread_id: str | None = None,
) -> AssistantState:
    root = Path(project_root or Path.cwd()).resolve()
    current = Path(cwd or root).resolve()
    return AssistantState(
        session_id=session_id or new_id("session"),
        thread_id=thread_id or new_id("thread"),
        project_root=str(root),
        cwd=str(current),
        input_text=input_text,
        input_kind=input_kind,  # type: ignore[typeddict-item]
        messages=[],
        attachments=[],
        active_command=None,
        active_skill=None,
        available_tools={},
        available_commands={},
        available_skills={},
        pending_tool_calls=[],
        tool_results=[],
        pending_confirmation=None,
        permissions={},
        permission_decisions=[],
        plan_mode={"enabled": False, "approved": False},
        todos=[],
        tasks=[],
        memory={},
        context_status={},
        usage={},
        mcp_state={},
        plugin_state={},
        hooks_state={},
        child_runs=[],
        artifacts=[],
        exported_outputs=[],
        errors=[],
        ui_events=[],
        final_response=None,
        metadata={},
    )

