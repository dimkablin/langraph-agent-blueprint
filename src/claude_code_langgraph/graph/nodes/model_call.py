"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.llm import ModelRequest
from claude_code_langgraph.models.messages import event


def model_call_node(state: dict, deps: AppDependencies) -> dict:
    if state.get("final_response") and not state.get("pending_tool_calls"):
        return {}
    available_tools = state.get("available_tools", {})
    allowed_tools = state.get("metadata", {}).get("allowed_tools_override")
    if allowed_tools:
        available_tools = {name: meta for name, meta in available_tools.items() if name in set(allowed_tools)}
    request = ModelRequest(
        messages=state.get("messages", []),
        system_context=state.get("context_status", {}).get("system_context", ""),
        tools=available_tools,
        metadata={"tool_results": state.get("tool_results", [])},
    )
    response = deps.model_provider.generate(request)
    usage = deps.usage_service.merge(state.get("usage", {}), response.usage.model_dump(mode="json"))
    events = [event("node_started", node="model_call")]
    if response.content:
        events.append(event("model_message", content=response.content))
    for token in response.content.split():
        events.append(event("model_token", token=token))
    message = AIMessage(
        content=response.content,
        tool_calls=[{"id": call["id"], "name": call["name"], "args": call.get("args", {})} for call in response.tool_calls],
    )
    return {
        "messages": [message],
        "pending_tool_calls": response.tool_calls,
        "usage": usage,
        "final_response": response.content if not response.tool_calls else None,
        "ui_events": [*events, event("node_finished", node="model_call")],
    }
