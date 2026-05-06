"""Main LangGraph builder and runtime facade shared by CLI, API, frontend, and tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from langgraph_agent_blueprint.dependencies import AppDependencies

from .checkpoints import default_checkpointer
from .nodes.bootstrap_config import bootstrap_config_node
from .nodes.command_router import command_router_node
from .nodes.compact_context import compact_context_node
from .nodes.compact_decision import compact_decision_node
from .nodes.context_builder import context_builder_node
from .nodes.error_recovery import error_recovery_node
from .nodes.finalize_response import finalize_response_node
from .nodes.hook_runner import hook_runner_node
from .nodes.load_registries import load_registries_node
from .nodes.model_call import model_call_node
from .nodes.normalize_input import normalize_input_node
from .nodes.permission_gate import permission_gate_node
from .nodes.plugin_policy import plugin_policy_node
from .nodes.persist_session import persist_session_node
from .nodes.skill_router import skill_router_node
from .nodes.tool_executor import tool_executor_node
from .nodes.tool_router import tool_router_node
from .routing import (
    route_after_command,
    route_after_compact_decision,
    route_after_permission,
    route_after_plugin_policy,
    route_after_tool_execution,
    route_after_tool_router,
)
from .state import AssistantState, create_initial_state
from .subgraphs.agent_graph import build_agent_graph
from .subgraphs.mcp_graph import build_mcp_graph


def build_main_graph(deps: AppDependencies) -> StateGraph:
    """Build the main LangGraph StateGraph for assistant runtime."""

    graph = StateGraph(AssistantState)
    graph.add_node("bootstrap_config", lambda state: bootstrap_config_node(state, deps))
    graph.add_node("load_registries", lambda state: load_registries_node(state, deps))
    graph.add_node("normalize_input", lambda state: normalize_input_node(state, deps))
    graph.add_node("command_router", lambda state: command_router_node(state, deps))
    graph.add_node("skill_graph", build_skill_node(deps))
    graph.add_node("plugin_policy", lambda state: plugin_policy_node(state, deps))
    graph.add_node("context_builder", lambda state: context_builder_node(state, deps))
    graph.add_node("model_call", lambda state: model_call_node(state, deps))
    graph.add_node("tool_router", lambda state: tool_router_node(state, deps))
    graph.add_node("permission_gate", lambda state: permission_gate_node(state, deps))
    graph.add_node("tool_executor", lambda state: tool_executor_node(state, deps))
    graph.add_node("hook_runner", lambda state: hook_runner_node(state, deps))
    graph.add_node("agent_graph", build_agent_graph(deps).compile())
    graph.add_node("mcp_graph", build_mcp_graph(deps).compile())
    graph.add_node("compact_decision", lambda state: compact_decision_node(state, deps))
    graph.add_node("compact_context", lambda state: compact_context_node(state, deps))
    graph.add_node("persist_session", lambda state: persist_session_node(state, deps))
    graph.add_node("finalize_response", lambda state: finalize_response_node(state, deps))
    graph.add_node("error_recovery", lambda state: error_recovery_node(state, deps))

    graph.add_edge(START, "bootstrap_config")
    graph.add_edge("bootstrap_config", "load_registries")
    graph.add_edge("load_registries", "normalize_input")
    graph.add_edge("normalize_input", "command_router")
    graph.add_conditional_edges(
        "command_router",
        route_after_command,
        {
            "persist_session": "persist_session",
            "plugin_policy": "plugin_policy",
            "context_builder": "context_builder",
            "skill_graph": "skill_graph",
            "compact_decision": "compact_decision",
            "error_recovery": "error_recovery",
        },
    )
    graph.add_conditional_edges("plugin_policy", route_after_plugin_policy, {"skill_graph": "skill_graph", "context_builder": "context_builder"})
    graph.add_edge("skill_graph", "context_builder")
    graph.add_edge("context_builder", "model_call")
    graph.add_edge("model_call", "tool_router")
    graph.add_conditional_edges(
        "tool_router",
        route_after_tool_router,
        {
            "no_tools": "hook_runner",
            "execute": "tool_executor",
            "needs_permission": "permission_gate",
            "rejected": "model_call",
            "skill_tool": "skill_graph",
            "agent_tool": "agent_graph",
            "mcp_tool": "mcp_graph",
            "error": "error_recovery",
        },
    )
    graph.add_conditional_edges("permission_gate", route_after_permission, {"execute": "tool_executor", "rejected": "model_call"})
    graph.add_conditional_edges("tool_executor", route_after_tool_execution, {"model_call": "model_call", "error_recovery": "error_recovery"})
    graph.add_edge("agent_graph", "model_call")
    graph.add_edge("mcp_graph", "model_call")
    graph.add_edge("hook_runner", "compact_decision")
    graph.add_conditional_edges("compact_decision", route_after_compact_decision, {"compact_context": "compact_context", "persist_session": "persist_session"})
    graph.add_edge("compact_context", "persist_session")
    graph.add_edge("error_recovery", "persist_session")
    graph.add_edge("persist_session", "finalize_response")
    graph.add_edge("finalize_response", END)
    return graph


def build_skill_node(deps: AppDependencies):
    """Wrap the skill router as a graph node closure with injected dependencies."""

    def node(state: dict) -> dict:
        return skill_router_node(state, deps)

    return node


class AssistantGraphRuntime:
    """Facade for invoking the same LangGraph runtime from CLI, API, and tests."""

    def __init__(self, dependencies: AppDependencies) -> None:
        self.dependencies = dependencies
        self.checkpointer = default_checkpointer()
        self.app = build_main_graph(dependencies).compile(checkpointer=self.checkpointer)

    def invoke(
        self,
        input_text: str,
        input_kind: str = "headless",
        session_id: str | None = None,
        thread_id: str | None = None,
        project_root: str | Path | None = None,
    ) -> dict[str, Any]:
        """Run one graph turn, hydrating persisted session state when a session id is supplied."""

        state = create_initial_state(
            input_text,
            project_root=project_root or self.dependencies.config.project_root or Path.cwd(),
            cwd=self.dependencies.config.cwd or project_root or self.dependencies.config.project_root or Path.cwd(),
            input_kind=input_kind,
            session_id=session_id,
            thread_id=thread_id,
        )
        if session_id:
            self._hydrate_session_state(state)
        config = {"configurable": {"thread_id": state["thread_id"]}}
        return self.app.invoke(state, config)

    def resume(self, thread_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        return self.app.invoke(Command(resume=decision), {"configurable": {"thread_id": thread_id}})

    def stream(self, input_text: str, input_kind: str = "headless") -> Iterable[dict[str, Any]]:
        """Yield newly appended UI events from LangGraph value-stream state updates."""

        previous_count = 0
        state = create_initial_state(
            input_text,
            project_root=self.dependencies.config.project_root or Path.cwd(),
            cwd=self.dependencies.config.cwd or self.dependencies.config.project_root or Path.cwd(),
            input_kind=input_kind,
        )
        for chunk in self.app.stream(
            state,
            {"configurable": {"thread_id": state["thread_id"]}},
            stream_mode="values",
        ):
            events = chunk.get("ui_events", [])
            for item in events[previous_count:]:
                yield item
            previous_count = len(events)

    def _hydrate_session_state(self, state: dict[str, Any]) -> None:
        """Mutate initial state with persisted session messages, todos, memory, usage, and metadata."""

        try:
            loaded = self.dependencies.session_storage.load_session(state["project_root"], state["session_id"])
        except (FileNotFoundError, OSError):
            return
        state["messages"] = loaded.get("messages", [])
        state["todos"] = loaded.get("todos", [])
        state["memory"] = loaded.get("memory", {})
        state["usage"] = loaded.get("usage", {})
        metadata = {**loaded.get("metadata", {}), **state.get("metadata", {})}
        metadata["resumed_from_session"] = state["session_id"]
        for key in [
            "input_normalized",
            "graph_finished",
            "tool_route",
            "compact_route",
            "compact_requested",
            "clear_messages",
            "export_requested",
            "doctor_requested",
            "allowed_tools_override",
            "active_skill_name",
            "skill_invocation",
        ]:
            metadata.pop(key, None)
        state["metadata"] = metadata
