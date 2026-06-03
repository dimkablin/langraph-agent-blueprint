"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json
from time import perf_counter

from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.graph.instrumentation import duration_ms, runtime_metrics_update
from langgraph_agent_blueprint.graph.run_control import cancellation_update
from langgraph_agent_blueprint.models import ModelRequest, ModelResponse, ToolCall, dump_model, event, validate_list


def model_call_node(state: dict, deps: AppDependencies) -> dict:
    """Call the configured model provider and translate its response into graph state.

    The node narrows tool schemas for active skills, preserves assistant tool calls on the
    AIMessage, and leaves actual tool execution to the downstream tool router.
    """

    cancelled = cancellation_update(state, deps, node="model_call")
    if cancelled is not None:
        return cancelled
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
    tool_schema_payload_chars = _json_size(available_tools)
    request = ModelRequest(
        messages=current.get("messages", []),
        system_context=current.get("context_status", {}).get("system_context", ""),
        tools=available_tools,
        metadata={
            "tool_results": current.get("tool_results", []),
            "model_intelligence": current.get("metadata", {}).get("model_intelligence"),
        },
    )
    model_start = perf_counter()
    response = _generate_model_response(current, deps, request)
    model_provider_duration_ms = duration_ms(model_start)
    cancelled = cancellation_update(current, deps, node="model_call")
    if cancelled is not None:
        return merge_updates(pre_update, cancelled)
    tool_calls = validate_list(ToolCall, response.tool_calls)
    usage = deps.usage_service.merge(current.get("usage", {}), response.usage.model_dump(mode="json"))
    events = [event("node_started", node="model_call")]
    if response.content:
        events.append(event("model_message", content=response.content))
    events.append(event("usage_updated", usage=usage))
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
        **runtime_metrics_update(
            current,
            {},
            extra_metrics={
                "model_provider_duration_ms": model_provider_duration_ms,
                "tool_schema_payload_chars": tool_schema_payload_chars,
                "tool_schema_token_estimate": _rough_token_estimate(tool_schema_payload_chars),
            },
        ),
    }
    post_update = run_hook_point(deps, state_with_update(current, update), "post_model")
    return merge_updates(pre_update, update, post_update)


def _generate_model_response(state: dict, deps: AppDependencies, request: ModelRequest) -> ModelResponse:
    if not state.get("metadata", {}).get("streaming_enabled"):
        return deps.model_provider.generate(request)

    writer = get_stream_writer()
    response: ModelResponse | None = None
    cancelled = False
    for stream_event in deps.model_provider.stream_generate(request):
        if deps.run_control_service.is_cancelled(str(state.get("thread_id") or "")):
            cancelled = True
            break
        if stream_event.type == "token" and stream_event.token:
            writer(event("model_token", session_id=state["session_id"], node="model_call", token=stream_event.token))
        elif stream_event.type == "response" and stream_event.response is not None:
            response = stream_event.response
    if cancelled:
        return ModelResponse()
    return response or deps.model_provider.generate(request)


def _json_size(payload: object) -> int:
    """Return a stable JSON character count without exposing payload contents."""

    try:
        return len(json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True))
    except TypeError:
        return len(str(payload))


def _rough_token_estimate(chars: int) -> int:
    return max(1, (chars + 3) // 4) if chars else 0
