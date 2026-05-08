"""Typed hook invocation dispatcher."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph_agent_blueprint.hooks import HookRegistry
from langgraph_agent_blueprint.models import (
    HookContext,
    HookContribution,
    HookInvocation,
    HookResult,
    HookRunSummary,
    HookRuntimeMetadata,
    event,
)


HookHandler = Callable[[HookInvocation], HookResult | list[HookResult] | None]
PLUGIN_ALLOWED_ACTIONS = {"continue", "add_event", "add_system_context", "modify_metadata", "block"}


class HookService:
    """Dispatch registered hook contributions and isolate hook failures."""

    def __init__(self, registry: HookRegistry | None = None, crash_on_error: bool = False) -> None:
        self.registry = registry or HookRegistry()
        self.crash_on_error = crash_on_error
        self._handlers: dict[str, HookHandler] = {}

    def register_handler(self, hook_id: str, handler: HookHandler) -> None:
        """Register a trusted in-process handler for one hook id."""

        self._handlers[hook_id] = handler

    def run(self, context: HookContext) -> HookRunSummary:
        """Run enabled hooks for `context.hook_point` and return typed results/events."""

        results: list[HookResult] = []
        events: list[dict[str, Any]] = []
        for hook in self.registry.get_for_point(context.hook_point):
            events.append(
                event(
                    "hook_started",
                    hook_id=hook.id,
                    hook_point=hook.hook_point,
                    plugin_name=hook.plugin_name,
                )
            )
            invocation = HookInvocation(hook=hook, context=context)
            try:
                hook_results = self._invoke(invocation)
                for result in hook_results:
                    results.append(result)
                    events.append(
                        event(
                            "hook_finished",
                            hook_id=hook.id,
                            hook_point=hook.hook_point,
                            plugin_name=hook.plugin_name,
                            action=result.action,
                            severity=result.severity,
                            message=result.message,
                        )
                    )
            except Exception as exc:
                if self.crash_on_error:
                    raise
                message = str(exc)
                results.append(HookResult(hook_id=hook.id, hook_point=hook.hook_point, action="error", message=message, severity="error"))
                events.append(
                    event(
                        "hook_error",
                        hook_id=hook.id,
                        hook_point=hook.hook_point,
                        plugin_name=hook.plugin_name,
                        error=message,
                        severity="error",
                    )
                )
        return HookRunSummary(hook_point=context.hook_point, results=results, events=events)

    def _invoke(self, invocation: HookInvocation) -> list[HookResult]:
        handler = self._handlers.get(invocation.hook.id)
        raw = handler(invocation) if handler else self._run_declarative(invocation)
        if raw is None:
            return [HookResult(hook_id=invocation.hook.id, hook_point=invocation.context.hook_point)]
        if isinstance(raw, HookResult):
            results = [raw]
        else:
            results = list(raw)
        return [self._normalize_result(invocation.hook, result) for result in results]

    def _run_declarative(self, invocation: HookInvocation) -> HookResult:
        runtime = _runtime_metadata(invocation.hook)
        if not invocation.hook.trusted and runtime.action not in PLUGIN_ALLOWED_ACTIONS:
            return HookResult(
                hook_id=invocation.hook.id,
                hook_point=invocation.context.hook_point,
                action="error",
                message=f"Hook action {runtime.action} is not allowed for untrusted plugin hooks.",
                severity="warning",
            )
        data: dict[str, Any] = {"plugin_name": invocation.hook.plugin_name}
        if runtime.content is not None:
            data["content"] = runtime.content
        if runtime.event_type is not None:
            data["event_type"] = runtime.event_type
        if runtime.event_data:
            data["event_data"] = runtime.event_data
        if runtime.metadata_update:
            data["metadata"] = runtime.metadata_update
        if runtime.context_update:
            data["context"] = runtime.context_update
        return HookResult(
            hook_id=invocation.hook.id,
            hook_point=invocation.context.hook_point,
            action=runtime.action,
            data=data,
            message=runtime.block_reason,
        )

    @staticmethod
    def _normalize_result(hook: HookContribution, result: HookResult) -> HookResult:
        data = dict(result.data)
        if hook.plugin_name and "plugin_name" not in data:
            data["plugin_name"] = hook.plugin_name
        return result.model_copy(update={"hook_id": hook.id, "hook_point": hook.hook_point, "data": data})


def _runtime_metadata(hook: HookContribution) -> HookRuntimeMetadata:
    raw = hook.metadata.get("runtime") if isinstance(hook.metadata, dict) else None
    if raw is None:
        raw = hook.metadata
    return HookRuntimeMetadata.model_validate(raw or {})
