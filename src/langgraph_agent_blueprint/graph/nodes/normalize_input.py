"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.context import parse_context_references
from langgraph_agent_blueprint.graph.hooks import merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models import AttachmentRef, ContextReference, dump_model, event, validate_list


def normalize_input_node(state: dict, deps: AppDependencies) -> dict:
    """Convert raw turn input into a HumanMessage exactly once per graph invocation."""

    if state.get("metadata", {}).get("input_normalized"):
        return {}
    metadata = {**state.get("metadata", {}), "input_normalized": True}
    attachments = [dump_model(item) for item in validate_list(AttachmentRef, state.get("attachments", []))]
    existing_refs = validate_list(ContextReference, state.get("context_references", []))
    parsed_refs = parse_context_references(state.get("input_text", ""))
    context_references = [dump_model(item) for item in [*existing_refs, *parsed_refs]]
    message = HumanMessage(content=state.get("input_text", ""))
    update = {
        "messages": [message],
        "attachments": attachments,
        "context_references": context_references,
        "metadata": metadata,
        "ui_events": [event("node_finished", node="normalize_input")],
    }
    hook_update = run_hook_point(deps, state_with_update(state, update), "user_prompt")
    return merge_updates(update, hook_update)

