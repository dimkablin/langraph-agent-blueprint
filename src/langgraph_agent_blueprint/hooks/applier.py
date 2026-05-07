"""Controlled HookResult application helpers."""

from __future__ import annotations

from typing import Any

from langgraph_agent_blueprint.models.hooks import HookResult
from langgraph_agent_blueprint.models.messages import event


def apply_hook_results(state: dict[str, Any], results: list[HookResult]) -> dict[str, Any]:
    """Convert typed hook results into a restricted LangGraph state update."""

    update: dict[str, Any] = {}
    metadata = dict(state.get("metadata", {}))
    context_status = dict(state.get("context_status", {}))
    hooks_state = dict(state.get("hooks_state", {}))
    ui_events: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    metadata_changed = False
    context_changed = False
    hooks_changed = False

    for result in results:
        if result.action == "continue":
            continue
        if result.action == "add_event":
            ui_events.append(
                event(
                    "hook_event",
                    hook_id=result.hook_id,
                    hook_point=result.hook_point,
                    payload=result.data.get("event_data", result.data),
                    severity=result.severity,
                )
            )
        elif result.action == "add_system_context":
            content = str(result.data.get("content") or result.message or "").strip()
            if not content:
                continue
            fragment = _system_context_fragment(result, content)
            metadata["hook_system_context_fragments"] = [*list(metadata.get("hook_system_context_fragments", [])), fragment]
            hooks_state["system_context_fragments"] = [
                *list(hooks_state.get("system_context_fragments", [])),
                {"hook_id": result.hook_id, "hook_point": result.hook_point, "content": fragment},
            ]
            existing = str(context_status.get("system_context") or "")
            context_status["system_context"] = f"{existing}\n\n{fragment}".strip() if existing else fragment
            metadata_changed = True
            context_changed = True
            hooks_changed = True
        elif result.action == "modify_metadata":
            payload = result.data.get("metadata", {})
            if isinstance(payload, dict):
                metadata["hook_metadata"] = {**dict(metadata.get("hook_metadata", {})), result.hook_id: payload}
                metadata_changed = True
        elif result.action == "modify_context":
            payload = result.data.get("context_status") or result.data.get("context") or {}
            if isinstance(payload, dict):
                safe_payload = {key: value for key, value in payload.items() if key in {"system_context", "estimated_tokens", "summary"}}
                if safe_payload:
                    context_status.update(safe_payload)
                    context_changed = True
        elif result.action == "block":
            reason = result.message or result.data.get("reason") or f"Blocked by hook {result.hook_id}"
            metadata["hook_blocked"] = {"hook_id": result.hook_id, "hook_point": result.hook_point, "reason": reason}
            update["final_response"] = str(reason)
            ui_events.append(
                event("hook_blocked", hook_id=result.hook_id, hook_point=result.hook_point, reason=reason, severity=result.severity)
            )
            metadata_changed = True
        elif result.action == "request_permission":
            message = "HookResult action request_permission is not supported in this phase."
            if result.message:
                message = f"{message} Requested: {result.message}"
            errors.append({"message": message, "type": "HookPermissionUnsupported", "recoverable": True, "hook_id": result.hook_id})
            ui_events.append(event("hook_error", hook_id=result.hook_id, hook_point=result.hook_point, error=message, severity="warning"))
        elif result.action == "error":
            message = result.message or result.data.get("error") or f"Hook {result.hook_id} returned an error"
            errors.append({"message": str(message), "type": "HookError", "recoverable": True, "hook_id": result.hook_id})
            ui_events.append(event("hook_error", hook_id=result.hook_id, hook_point=result.hook_point, error=str(message), severity="error"))

    if metadata_changed:
        update["metadata"] = metadata
    if context_changed:
        update["context_status"] = context_status
    if hooks_changed:
        update["hooks_state"] = hooks_state
    if ui_events:
        update["ui_events"] = ui_events
    if errors:
        update["errors"] = errors
    return update


def _system_context_fragment(result: HookResult, content: str) -> str:
    plugin_name = result.data.get("plugin_name")
    if plugin_name:
        return f"[plugin hook: {result.hook_id}] {content}"
    return f"[hook: {result.hook_id}] {content}"
