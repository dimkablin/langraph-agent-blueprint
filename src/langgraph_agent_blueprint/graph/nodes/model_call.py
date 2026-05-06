"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.models.base import dump_model, validate_list
from langgraph_agent_blueprint.models.llm import ModelRequest
from langgraph_agent_blueprint.models.messages import event
from langgraph_agent_blueprint.models.tools import ToolCall


def model_call_node(state: dict, deps: AppDependencies) -> dict:
    """Call the configured model provider and translate its response into graph state.

    The node narrows tool schemas for active skills, preserves assistant tool calls on the
    AIMessage, and leaves actual tool execution to the downstream tool router.
    """

    if state.get("final_response") and not state.get("pending_tool_calls"):
        return {}
    pre_update = run_hook_point(deps, state, "pre_model")
    if hook_blocked(pre_update):
        return pre_update
    current = state_with_update(state, pre_update)
    available_tools = current.get("available_tools", {})
    allowed_tools = current.get("metadata", {}).get("allowed_tools_override")
    if allowed_tools:
        available_tools = {name: meta for name, meta in available_tools.items() if name in set(allowed_tools)}
    request = ModelRequest(
        messages=current.get("messages", []),
        system_context=current.get("context_status", {}).get("system_context", ""),
        tools=available_tools,
        metadata={"tool_results": current.get("tool_results", [])},
    )
    response = deps.model_provider.generate(request)
    tool_calls = validate_list(ToolCall, response.tool_calls)
    usage = deps.usage_service.merge(current.get("usage", {}), response.usage.model_dump(mode="json"))
    events = [event("node_started", node="model_call")]
    if response.content:
        events.append(event("model_message", content=response.content))
    for token in response.content.split():
        events.append(event("model_token", token=token))
    message = AIMessage(
        content=response.content,
        tool_calls=[{"id": call.id, "name": call.name, "args": call.args} for call in tool_calls],
    )
    update = {
        "messages": [message],
        "pending_tool_calls": [dump_model(call) for call in tool_calls],
        "usage": usage,
        "final_response": response.content if not tool_calls else None,
        "ui_events": [*events, event("node_finished", node="model_call")],
    }
    post_update = run_hook_point(deps, state_with_update(current, update), "post_model")
    return merge_updates(pre_update, update, post_update)
