"""Main LangGraph builder and runtime facade shared by CLI, API, frontend, and tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models import AttachmentRef, TraceContext, TraceMetadata, dump_model
from langgraph_agent_blueprint.utils.ids import validate_session_id, validate_thread_id

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
from .nodes.resolve_context import resolve_context_node
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
    graph.add_node("resolve_context", lambda state: resolve_context_node(state, deps))
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
            "context_builder": "resolve_context",
            "skill_graph": "skill_graph",
            "compact_decision": "compact_decision",
            "error_recovery": "error_recovery",
        },
    )
    graph.add_conditional_edges("plugin_policy", route_after_plugin_policy, {"skill_graph": "skill_graph", "context_builder": "resolve_context"})
    graph.add_edge("skill_graph", "resolve_context")
    graph.add_edge("resolve_context", "context_builder")
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
    graph.add_conditional_edges(
        "permission_gate",
        route_after_permission,
        {"execute": "tool_executor", "mcp_tool": "mcp_graph", "rejected": "model_call"},
    )
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
        turn_index: int | None = None,
        model_intelligence: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
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
        if attachments:
            state["attachments"] = [dump_model(AttachmentRef.model_validate(item)) for item in attachments]
        if model_intelligence:
            state["metadata"] = {**state.get("metadata", {}), "model_intelligence": model_intelligence}
        if turn_index is not None:
            state["metadata"] = {**state.get("metadata", {}), "turn_index": turn_index}
        trace_context = self._trace_context(state)
        with self.dependencies.observability_service.trace_turn(
            trace_context,
            self._trace_metadata(state),
            input_data={"input_text": input_text, "input_kind": input_kind},
            name="lg-agent chat turn",
        ) as trace:
            config = trace.graph_config({"configurable": {"thread_id": state["thread_id"]}}, self._trace_metadata(state))
            result = self.app.invoke(state, config)
            result_context = self._trace_context(result) if isinstance(result, dict) else trace_context
            trace.record_runtime_events(result.get("ui_events", []) if isinstance(result, dict) else [], result_context)
            if isinstance(result, dict):
                trace.set_output(result.get("final_response"))
        return result

    def resume(self, thread_id: str, decision: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
        thread_id = validate_thread_id(thread_id)
        if session_id is not None:
            session_id = validate_session_id(session_id)
        initial_context = TraceContext(
            session_id=session_id or thread_id,
            thread_id=thread_id,
            environment=self.dependencies.config.langfuse.environment,
            release=self.dependencies.config.langfuse.release,
            user_id=self.dependencies.config.langfuse.trace_user_id,
        )
        with self.dependencies.observability_service.trace_turn(
            initial_context,
            self._trace_metadata({}),
            input_data={"resume": decision},
            name="lg-agent resume turn",
        ) as trace:
            config = trace.graph_config({"configurable": {"thread_id": thread_id}}, self._trace_metadata({}))
            result = self.app.invoke(Command(resume=decision), config)
            result_context = self._trace_context(result) if isinstance(result, dict) else initial_context
            trace.record_runtime_events(result.get("ui_events", []) if isinstance(result, dict) else [], result_context)
            if isinstance(result, dict):
                trace.set_output(result.get("final_response"))
        return result

    def stream(
        self,
        input_text: str,
        input_kind: str = "headless",
        session_id: str | None = None,
        thread_id: str | None = None,
        project_root: str | Path | None = None,
        turn_index: int | None = None,
        model_intelligence: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> Iterable[dict[str, Any]]:
        """Yield newly appended UI events from LangGraph value-stream state updates."""

        def generator() -> Iterable[dict[str, Any]]:
            previous_count = 0
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
            if attachments:
                state["attachments"] = [dump_model(AttachmentRef.model_validate(item)) for item in attachments]
            if model_intelligence:
                state["metadata"] = {**state.get("metadata", {}), "model_intelligence": model_intelligence}
            if turn_index is not None:
                state["metadata"] = {**state.get("metadata", {}), "turn_index": turn_index}
            final_chunk: dict[str, Any] | None = None
            trace_context = self._trace_context(state)
            with self.dependencies.observability_service.trace_turn(
                trace_context,
                self._trace_metadata(state),
                input_data={"input_text": input_text, "input_kind": input_kind},
                name="lg-agent chat turn",
            ) as trace:
                config = trace.graph_config({"configurable": {"thread_id": state["thread_id"]}}, self._trace_metadata(state))
                for chunk in self.app.stream(
                    state,
                    config,
                    stream_mode="values",
                ):
                    if isinstance(chunk, dict):
                        final_chunk = chunk
                        context = self._trace_context(chunk)
                        events = chunk.get("ui_events", [])
                    else:
                        context = trace_context
                        events = []
                    for item in events[previous_count:]:
                        trace.record_runtime_event(item, context)
                        yield item
                    previous_count = len(events)
                if final_chunk is not None:
                    trace.set_output(final_chunk.get("final_response"))

        return generator()

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
            "context_resolved",
        ]:
            metadata.pop(key, None)
        state["metadata"] = metadata

    def _graph_config(self, state: dict[str, Any]) -> dict[str, Any]:
        """Build LangGraph invocation config with observability callbacks and metadata."""

        return self.dependencies.observability_service.build_graph_config(
            {"configurable": {"thread_id": state["thread_id"]}},
            self._trace_context(state),
            self._trace_metadata(state),
        )

    def _record_result_events(self, result: dict[str, Any]) -> None:
        """Record accumulated UI events after graph invoke/resume returns."""

        if not isinstance(result, dict):
            return
        self.dependencies.observability_service.record_runtime_events(
            result.get("ui_events", []),
            self._trace_context(result),
        )

    def _trace_context(self, state: dict[str, Any]) -> TraceContext:
        config = self.dependencies.config
        project_root = state.get("project_root") or config.project_root or Path.cwd()
        safe_root, root_hash = self._safe_project_root(project_root)
        tags = ["runtime"]
        if config.llm_provider:
            tags.append(str(config.llm_provider))
        metadata = {"project_root_hash": root_hash}
        state_metadata = state.get("metadata", {}) if isinstance(state.get("metadata"), dict) else {}
        if "turn_index" in state_metadata:
            metadata["turn_index"] = state_metadata["turn_index"]
        return TraceContext(
            session_id=str(state.get("session_id") or "unknown"),
            thread_id=state.get("thread_id"),
            project_root=safe_root,
            user_id=config.langfuse.trace_user_id,
            environment=config.langfuse.environment,
            release=config.langfuse.release,
            tags=tags,
            metadata=metadata,
        )

    def _trace_metadata(self, state: dict[str, Any]) -> TraceMetadata:
        config = self.dependencies.config
        plugins = state.get("plugin_state", {}).get("plugins", []) if isinstance(state, dict) else []
        plugin_names = [str(plugin.get("name")) for plugin in plugins if plugin.get("name")]
        mcp_servers = list((config.mcp_config.get("servers") or {}).keys()) if isinstance(config.mcp_config, dict) else []
        active_skill = state.get("active_skill") if isinstance(state, dict) else None
        active_tool = (state.get("pending_tool_calls") or [{}])[0] if isinstance(state, dict) and state.get("pending_tool_calls") else None
        return TraceMetadata(
            provider=config.llm_provider,
            model=config.effective_model(),
            active_skill=active_skill.get("name") if isinstance(active_skill, dict) else None,
            active_tool=active_tool.get("name") if isinstance(active_tool, dict) else None,
            plugin_names=plugin_names,
            mcp_servers=[str(name) for name in mcp_servers],
            permission_mode=config.permission_mode,
        )

    def _safe_project_root(self, project_root: str | Path) -> tuple[str, str]:
        root_text = str(Path(project_root).resolve())
        root_hash = hashlib.sha256(root_text.encode("utf-8")).hexdigest()[:12]
        if self.dependencies.config.langfuse.include_project_paths:
            return root_text, root_hash
        return Path(root_text).name, root_hash
