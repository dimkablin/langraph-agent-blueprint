"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.config import get_stream_writer

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.graph.hooks import hook_blocked, merge_updates, run_hook_point, state_with_update
from langgraph_agent_blueprint.graph.instrumentation import duration_ms, runtime_metrics_update
from langgraph_agent_blueprint.graph.run_control import cancellation_update
from langgraph_agent_blueprint.models import ModelContextPart, ModelContextReport, ModelRequest, ModelResponse, ToolCall, dump_model, event, validate_list


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
    request, model_context = _fit_request_to_context_window(request, deps.config.context_max_tokens, tool_schema_payload_chars)
    context_usage = _usage_from_model_context(model_context)
    model_start = perf_counter()
    response = _generate_model_response(current, deps, request)
    response = _repair_missing_subagent_tool_calls(current, deps, request, response)
    model_provider_duration_ms = duration_ms(model_start)
    cancelled = cancellation_update(current, deps, node="model_call")
    if cancelled is not None:
        return merge_updates(pre_update, cancelled)
    tool_calls = validate_list(ToolCall, response.tool_calls)
    usage = {
        **deps.usage_service.merge(current.get("usage", {}), response.usage.model_dump(mode="json")),
        **context_usage,
    }
    model_context_payload = dump_model(model_context)
    events = [event("node_started", node="model_call"), event("model_context_prepared", node="model_call", model_context=model_context_payload)]
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
        "metadata": {**current.get("metadata", {}), "model_context": model_context_payload},
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


def _repair_missing_subagent_tool_calls(
    state: dict,
    deps: AppDependencies,
    request: ModelRequest,
    response: ModelResponse,
) -> ModelResponse:
    """Retry once when the model promises subagents but emits no agent tool calls."""

    tool_calls = validate_list(ToolCall, response.tool_calls)
    if tool_calls or not _needs_subagent_tool_repair(state, request, response):
        return response

    repair_request = request.model_copy(
        update={
            "messages": [
                *request.messages,
                AIMessage(content=response.content),
                SystemMessage(content=_SUBAGENT_TOOL_REPAIR_PROMPT),
            ]
        }
    )
    repaired = deps.model_provider.generate(repair_request)
    repaired_calls = validate_list(ToolCall, repaired.tool_calls)
    if not repaired_calls:
        return response

    first_usage = response.usage.model_dump(mode="json")
    repaired_usage = repaired.usage.model_dump(mode="json")
    usage = deps.usage_service.merge(first_usage, repaired_usage)
    content = response.content if response.content else repaired.content
    if response.content and repaired.content and repaired.content not in response.content:
        content = f"{response.content}\n\n{repaired.content}"
    return ModelResponse(
        content=content,
        tool_calls=[dump_model(call) for call in repaired_calls],
        usage=usage,
        raw=repaired.raw,
    )


_SUBAGENT_TOOL_REPAIR_PROMPT = (
    "The previous assistant message said subagents would be created, but it emitted no `agent` tool calls. "
    "This violates the tool-use contract. Continue now by calling the `agent` tool once for each requested "
    "child agent, for example backend and frontend. Do not repeat the promise in prose. If prerequisites are "
    "not actually complete, call the required tools; otherwise call `agent`."
)


def _needs_subagent_tool_repair(state: dict, request: ModelRequest, response: ModelResponse) -> bool:
    if "agent" not in request.tools:
        return False
    if _agent_called_after_latest_user(request.messages):
        return False
    user_text = _latest_user_text(request.messages)
    if not _has_subagent_intent(user_text):
        return False
    return _promises_subagent_work(response.content)


def _agent_called_after_latest_user(messages: list[object]) -> bool:
    for message in reversed(messages):
        message_type = getattr(message, "type", None)
        if message_type == "human":
            return False
        for call in list(getattr(message, "tool_calls", []) or []):
            if isinstance(call, dict) and call.get("name") == "agent":
                return True
    return False


def _latest_user_text(messages: list[object]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", None) == "human":
            return str(getattr(message, "content", "") or "")
    return ""


def _has_subagent_intent(text: str) -> bool:
    normalized = text.lower()
    if any(keyword in normalized for keyword in ("сабагент", "саб-агент", "subagent", "sub-agent")):
        return True
    agent_terms = ("agent", "агент")
    split_terms = (("frontend", "backend"), ("фронт", "бек"), ("react", "fastapi"), ("реакт", "фастапи"))
    return any(term in normalized for term in agent_terms) and any(
        left in normalized and right in normalized for left, right in split_terms
    )


def _promises_subagent_work(text: str) -> bool:
    normalized = text.lower()
    if not any(keyword in normalized for keyword in ("сабагент", "саб-агент", "subagent", "sub-agent", "agent", "агент")):
        return False
    promise_terms = (
        "созда",
        "запущ",
        "start",
        "create",
        "run",
        "spawn",
        "delegate",
        "now",
        "теперь",
    )
    return any(term in normalized for term in promise_terms)


def _json_size(payload: object) -> int:
    """Return a stable JSON character count without exposing payload contents."""

    try:
        return len(json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True))
    except TypeError:
        return len(str(payload))


def _rough_token_estimate(chars: int) -> int:
    return max(1, (chars + 3) // 4) if chars else 0


def _fit_request_to_context_window(
    request: ModelRequest,
    context_max_tokens: int,
    tool_schema_payload_chars: int,
) -> tuple[ModelRequest, ModelContextReport]:
    """Return the model request that will be sent plus a typed report for the frontend."""

    context_max = max(int(context_max_tokens or 0), 0)
    overhead_tokens = _rough_token_estimate(
        _text_payload_chars(request.system_context)
        + tool_schema_payload_chars
        + (_json_size(request.metadata) if request.metadata else 0)
    )
    message_budget = max(context_max - overhead_tokens, 0) if context_max else None
    messages, messages_truncated = _fit_messages_to_budget(request.messages, message_budget)
    fitted = request.model_copy(update={"messages": messages})
    report = _model_context_report(fitted, context_max, tool_schema_payload_chars, truncated=messages_truncated)
    return fitted, report


def _fit_messages_to_budget(messages: list[Any], token_budget: int | None) -> tuple[list[Any], bool]:
    if token_budget is None:
        return list(messages), False
    if token_budget <= 0:
        return list(messages), bool(messages)

    selected: list[Any] = []
    remaining = token_budget
    truncated = False
    for message in reversed(messages):
        tokens = _rough_token_estimate(_message_content_chars(message))
        if tokens <= remaining:
            selected.append(message)
            remaining -= tokens
            continue
        if not selected:
            truncated_message = _message_with_content(message, _truncate_text_payload(getattr(message, "content", ""), remaining))
            selected.append(truncated_message)
        truncated = True
        break
    return list(reversed(selected)), truncated or len(selected) < len(messages)


def _model_context_report(
    request: ModelRequest,
    context_max: int,
    tool_schema_payload_chars: int,
    *,
    truncated: bool,
) -> ModelContextReport:
    parts: list[ModelContextPart] = []
    if request.system_context:
        parts.append(
            ModelContextPart(
                kind="system",
                title="System context",
                content=request.system_context,
                token_estimate=_rough_token_estimate(_text_payload_chars(request.system_context)),
            )
        )
    for index, message in enumerate(request.messages, start=1):
        content = _text_payload_text(getattr(message, "content", ""))
        parts.append(
            ModelContextPart(
                kind="messages",
                title=f"Message {index}",
                content=content,
                token_estimate=_rough_token_estimate(len(content)),
                metadata={"role": str(getattr(message, "type", type(message).__name__))},
            )
        )
    if request.tools:
        content = _json_text(request.tools)
        parts.append(
            ModelContextPart(
                kind="tools",
                title="Tool schemas",
                content=content,
                token_estimate=_rough_token_estimate(tool_schema_payload_chars),
            )
        )
    if request.metadata:
        content = _json_text(request.metadata)
        parts.append(
            ModelContextPart(
                kind="metadata",
                title="Request metadata",
                content=content,
                token_estimate=_rough_token_estimate(len(content)),
            )
        )
    used_tokens = sum(part.token_estimate for part in parts)
    remaining_tokens = max(context_max - used_tokens, 0) if context_max else 0
    percent = round(min(100.0, max(0.0, (used_tokens / context_max) * 100)), 2) if context_max else 0
    return ModelContextReport(
        max_tokens=context_max,
        used_tokens=used_tokens,
        remaining_tokens=remaining_tokens,
        percent=percent,
        truncated=truncated or bool(context_max and used_tokens > context_max),
        parts=parts,
    )


def _usage_from_model_context(report: ModelContextReport) -> dict[str, int | float | bool]:
    return {
        "context_used": report.used_tokens,
        "context_max": report.max_tokens,
        "context_percent": report.percent,
        "context_truncated": report.truncated,
    }


def _message_content_chars(message: object) -> int:
    return _text_payload_chars(getattr(message, "content", ""))


def _text_payload_chars(payload: object) -> int:
    if payload is None:
        return 0
    if isinstance(payload, str):
        return len(payload)
    if isinstance(payload, bytes):
        return len(payload.decode("utf-8", errors="replace"))
    if isinstance(payload, (list, tuple, dict)):
        return _json_size(payload)
    return len(str(payload))


def _text_payload_text(payload: object) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        return payload.decode("utf-8", errors="replace")
    if isinstance(payload, (list, tuple, dict)):
        return _json_text(payload)
    return str(payload)


def _json_text(payload: object) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
    except TypeError:
        return str(payload)


def _truncate_text_payload(payload: object, max_tokens: int) -> object:
    text = _text_payload_text(payload)
    max_chars = max(1, max_tokens * 4)
    if len(text) <= max_chars:
        return payload
    return text[:max_chars].rstrip() + "\n[truncated to fit context window]"


def _message_with_content(message: Any, content: object) -> Any:
    if hasattr(message, "model_copy"):
        return message.model_copy(update={"content": content})
    return message
