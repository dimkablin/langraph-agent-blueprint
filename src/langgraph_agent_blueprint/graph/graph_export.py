"""LangGraph runtime module that defines state, routing, streaming, checkpoints, or graph construction."""

from __future__ import annotations


def mermaid_graph() -> str:
    """Return the documented main graph topology."""

    return """flowchart TD
    START --> bootstrap_config
    bootstrap_config --> load_registries
    load_registries --> normalize_input
    normalize_input --> command_router
    command_router -->|local command| persist_session
    command_router -->|prompt/model| context_builder
    command_router -->|manual compact| compact_decision
    command_router -->|skill| skill_graph
    context_builder --> compact_decision
    compact_decision -->|skip pre-model| model_call
    model_call --> tool_router
    tool_router -->|no tools| hook_runner
    tool_router -->|skill tool| skill_graph
    tool_router -->|agent tool| agent_graph
    tool_router -->|mcp tool| mcp_graph
    tool_router -->|needs permission| permission_gate
    tool_router -->|execute| tool_executor
    permission_gate -->|interrupt| HUMAN
    HUMAN -->|resume approve| tool_executor
    HUMAN -->|resume reject| compact_decision
    tool_executor --> compact_decision
    skill_graph --> context_builder
    agent_graph --> compact_decision
    mcp_graph --> compact_decision
    hook_runner --> persist_session
    compact_decision -->|compact| compact_context
    compact_decision -->|skip manual| persist_session
    compact_context -->|manual| persist_session
    compact_context -->|pre-model| model_call
    persist_session --> finalize_response
    finalize_response --> END"""

