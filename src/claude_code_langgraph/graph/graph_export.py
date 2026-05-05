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
    command_router -->|skill| skill_graph
    context_builder --> model_call
    model_call --> tool_router
    tool_router -->|no tools| compact_decision
    tool_router -->|skill tool| skill_graph
    tool_router -->|agent tool| agent_graph
    tool_router -->|mcp tool| mcp_graph
    tool_router -->|needs permission| permission_gate
    tool_router -->|execute| tool_executor
    permission_gate -->|interrupt| HUMAN
    HUMAN -->|resume approve| tool_executor
    HUMAN -->|resume reject| model_call
    tool_executor --> model_call
    skill_graph --> model_call
    agent_graph --> model_call
    mcp_graph --> model_call
    compact_decision -->|compact| compact_context
    compact_decision -->|skip| persist_session
    compact_context --> persist_session
    persist_session --> finalize_response
    finalize_response --> END"""

