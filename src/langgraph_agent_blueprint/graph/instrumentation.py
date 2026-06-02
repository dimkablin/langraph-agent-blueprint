"""Small runtime latency instrumentation helpers for LangGraph nodes and turns."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any

from langgraph_agent_blueprint.models import event

NodeCallable = Callable[[dict[str, Any]], dict[str, Any]]


def duration_ms(start: float) -> float:
    """Return a compact millisecond duration from a ``perf_counter`` start value."""

    return round((perf_counter() - start) * 1000, 3)


def timed_node(name: str, node: NodeCallable) -> NodeCallable:
    """Wrap a graph node so each turn records safe per-node latency metadata.

    The wrapper emits only node names and numeric timings. It never inspects prompt,
    message, tool argument, or model output contents.
    """

    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        start = perf_counter()
        try:
            update = node(state)
        except Exception:
            elapsed_ms = duration_ms(start)
            metrics_update = runtime_metrics_update(state, {}, node_duration={name: elapsed_ms})
            failure_event = event(
                "node_finished",
                session_id=str(state.get("session_id") or "unknown"),
                node=name,
                duration_ms=elapsed_ms,
                status="error",
            )
            metrics_update["ui_events"] = [failure_event]
            # The graph will not apply this update because the exception escapes, but
            # keeping the failure path side-effect-free preserves normal error routing.
            raise
        if not isinstance(update, dict):
            return update
        elapsed_ms = duration_ms(start)
        instrumented = dict(update)
        instrumented["observability_state"] = runtime_metrics_update(
            state,
            update,
            node_duration={name: elapsed_ms},
        )["observability_state"]
        events = list(update.get("ui_events", []) or [])
        events.extend(
            [
                event("node_started", session_id=str(state.get("session_id") or "unknown"), node=name),
                event(
                    "node_finished",
                    session_id=str(state.get("session_id") or "unknown"),
                    node=name,
                    duration_ms=elapsed_ms,
                    status="ok",
                ),
            ]
        )
        instrumented["ui_events"] = events
        return instrumented

    return wrapped


def runtime_metrics_update(
    state: Mapping[str, Any],
    update: Mapping[str, Any],
    *,
    node_duration: Mapping[str, float] | None = None,
    extra_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an ``observability_state`` update preserving prior runtime metrics."""

    current = _runtime_metrics_from(state)
    incoming = _runtime_metrics_from(update)
    metrics = _merge_metrics(current, incoming)
    if node_duration:
        node_durations = dict(metrics.get("node_durations_ms", {}))
        for node_name, elapsed_ms in node_duration.items():
            node_durations[node_name] = round(float(node_durations.get(node_name, 0.0)) + float(elapsed_ms), 3)
        metrics["node_durations_ms"] = node_durations
    if extra_metrics:
        extras = dict(extra_metrics)
        if isinstance(extras.get("tool_durations_ms"), list):
            current_tools = list(metrics.get("tool_durations_ms", [])) if isinstance(metrics.get("tool_durations_ms"), list) else []
            extras["tool_durations_ms"] = [*current_tools, *extras["tool_durations_ms"]]
        metrics = _merge_metrics(metrics, extras)
    return {"observability_state": {"runtime_metrics": metrics}}


def runtime_metrics_event(
    state: Mapping[str, Any],
    *,
    total_duration_ms: float,
    event_count: int,
) -> dict[str, Any]:
    """Create a safe turn-level metrics event from accumulated numeric state."""

    metrics = _runtime_metrics_from(state)
    metrics["total_duration_ms"] = round(total_duration_ms, 3)
    metrics["event_count"] = int(event_count)
    return event(
        "runtime_metrics",
        session_id=str(state.get("session_id") or "unknown"),
        node="runtime",
        metrics=_sorted_metrics(metrics),
    )


def _runtime_metrics_from(value: Mapping[str, Any]) -> dict[str, Any]:
    observability_state = value.get("observability_state") if isinstance(value, Mapping) else None
    if not isinstance(observability_state, Mapping):
        return {}
    metrics = observability_state.get("runtime_metrics")
    return dict(metrics) if isinstance(metrics, Mapping) else {}


def _merge_metrics(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in incoming.items():
        if key == "node_durations_ms" and isinstance(value, Mapping):
            current = dict(merged.get(key, {})) if isinstance(merged.get(key), Mapping) else {}
            current.update({str(item_key): item_value for item_key, item_value in value.items()})
            merged[key] = current
        elif key == "tool_durations_ms" and isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value
    return merged


def _sorted_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    sorted_metrics = dict(metrics)
    node_durations = sorted_metrics.get("node_durations_ms")
    if isinstance(node_durations, Mapping):
        sorted_metrics["node_durations_ms"] = dict(sorted(node_durations.items()))
    return sorted_metrics
