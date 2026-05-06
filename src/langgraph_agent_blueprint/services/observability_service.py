"""Optional Langfuse observability integration for graph runs and RuntimeEvents."""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from langgraph_agent_blueprint.models.events import RuntimeEvent
from langgraph_agent_blueprint.models.observability import LangfuseConfig, ObservabilityEvent, TraceContext, TraceMetadata


SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "cookie",
    "key",
    "password",
    "secret",
    "token",
)
OUTPUT_EVENT_TYPES = {"final_response", "tool_call_finished", "mcp_tool_call_finished", "model_message"}
INPUT_EVENT_TYPES = {"command_started", "model_message", "tool_call_started", "mcp_tool_call_started"}
IMPORTANT_RUNTIME_EVENTS = {
    "session_started",
    "command_started",
    "command_finished",
    "model_message",
    "tool_call_started",
    "tool_call_finished",
    "tool_call_error",
    "permission_required",
    "permission_resolved",
    "skill_started",
    "skill_finished",
    "hook_started",
    "hook_finished",
    "hook_blocked",
    "hook_error",
    "mcp_server_connected",
    "mcp_tools_discovered",
    "mcp_tool_call_started",
    "mcp_tool_call_finished",
    "mcp_tool_call_error",
    "compact_started",
    "compact_finished",
    "session_persisted",
    "final_response",
    "error",
}


class LangfuseCallbackFactory:
    """Factory that isolates optional Langfuse imports from the base runtime."""

    def create_client(self, config: LangfuseConfig) -> Any:
        """Create the Langfuse SDK client using explicit config, not logged env state."""

        try:
            from langfuse import Langfuse
        except ImportError:
            from langfuse.otel import Langfuse  # type: ignore[no-redef]

        kwargs = {
            "public_key": config.public_key,
            "secret_key": config.secret_key,
            "debug": config.debug,
            "tracing_enabled": True,
            "environment": config.environment,
            "release": config.release,
        }
        variants = [
            {**kwargs, "base_url": config.base_url},
            {**kwargs, "host": config.base_url},
            kwargs,
        ]
        for variant in variants:
            clean = {key: value for key, value in variant.items() if value is not None}
            try:
                return Langfuse(**clean)
            except TypeError:
                continue
        return Langfuse()

    def create_callback_handler(self, config: LangfuseConfig, trace_context: TraceContext) -> Any:
        """Create a LangChain/LangGraph callback handler for automatic tracing."""

        from langfuse.langchain import CallbackHandler

        kwargs = {
            "public_key": config.public_key,
            "secret_key": config.secret_key,
            "environment": config.environment,
            "release": config.release,
        }
        variants = [
            {**kwargs, "base_url": config.base_url},
            {**kwargs, "host": config.base_url},
            kwargs,
            {},
        ]
        for variant in variants:
            clean = {key: value for key, value in variant.items() if value is not None}
            try:
                return CallbackHandler(**clean)
            except TypeError:
                continue
        return CallbackHandler()


class RuntimeEventTraceMapper:
    """Map RuntimeEvent records into small, redacted Langfuse event payloads."""

    def __init__(self, config: LangfuseConfig) -> None:
        self.config = config

    def map(self, event: RuntimeEvent | dict[str, Any], trace_context: TraceContext) -> dict[str, Any] | None:
        """Return a backend payload for important runtime events."""

        try:
            runtime_event = RuntimeEvent.model_validate(event)
        except ValidationError:
            return None
        if runtime_event.type not in IMPORTANT_RUNTIME_EVENTS:
            return None
        data = self._event_data(runtime_event)
        event_model = ObservabilityEvent(
            type="runtime",
            name=f"runtime.{runtime_event.type}",
            session_id=trace_context.session_id,
            severity=runtime_event.severity,
            data=data if isinstance(data, dict) else {"value": data},
        )
        output = data if runtime_event.type in OUTPUT_EVENT_TYPES else None
        input_payload = data if runtime_event.type not in OUTPUT_EVENT_TYPES else None
        metadata = {
            "runtime_event_id": runtime_event.id,
            "runtime_event_type": runtime_event.type,
            "session_id": trace_context.session_id,
            "thread_id": trace_context.thread_id,
            "environment": trace_context.environment,
            "release": trace_context.release,
            "node": runtime_event.node,
            "severity": runtime_event.severity,
            **trace_context.metadata,
        }
        return {
            "name": event_model.name,
            "input": input_payload,
            "output": output,
            "metadata": self.redact(metadata),
            "level": self._level(runtime_event.severity),
            "status_message": runtime_event.data.get("error") or runtime_event.data.get("reason"),
        }

    def _event_data(self, event: RuntimeEvent) -> dict[str, Any] | str:
        data = copy.deepcopy(event.data)
        if event.type in INPUT_EVENT_TYPES and not self.config.capture_inputs:
            return "<redacted>"
        if event.type in OUTPUT_EVENT_TYPES and not self.config.capture_outputs:
            return "<redacted>"
        return self.redact(data)

    def redact(self, value: Any) -> Any:
        """Redact sensitive keys and keep payloads bounded."""

        redacted = self._redact_value(value)
        return self._truncate(redacted)

    def _redact_value(self, value: Any, key: str | None = None) -> Any:
        if key and any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
            return "***" if value not in (None, "") else None
        if isinstance(value, dict):
            return {str(item_key): self._redact_value(item_value, str(item_key)) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._redact_value(item) for item in value]
        return value

    def _truncate(self, value: Any) -> Any:
        limit = max(256, int(self.config.max_event_chars))
        try:
            rendered = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            rendered = str(value)
        if len(rendered) <= limit:
            return value
        if isinstance(value, str):
            return value[:limit] + "...<truncated>"
        return {"truncated": True, "preview": rendered[:limit] + "...<truncated>"}

    @staticmethod
    def _level(severity: str) -> str:
        if severity == "error":
            return "ERROR"
        if severity == "warning":
            return "WARNING"
        return "DEFAULT"


class ObservabilityService:
    """Dispatcher for optional Langfuse callbacks and RuntimeEvent tracing."""

    def __init__(self, config: LangfuseConfig | None = None, factory: Any | None = None) -> None:
        self.config = config or LangfuseConfig()
        self.factory = factory or LangfuseCallbackFactory()
        self.mapper = RuntimeEventTraceMapper(self.config)
        self._client: Any | None = None
        self._client_checked = False
        self._sdk_installed: bool | None = None
        self._last_error: str | None = None

    @property
    def client_events(self) -> list[dict[str, Any]]:
        client = self._client
        events = getattr(client, "events", None)
        return events if isinstance(events, list) else []

    def is_enabled(self) -> bool:
        return bool(self.config.enabled)

    def get_callbacks(self, trace_context: TraceContext) -> list[Any]:
        """Return LangGraph callbacks, or an empty list if disabled/unavailable."""

        if not self.is_enabled():
            return []
        if not self._has_credentials():
            self._last_error = "Langfuse enabled but public/secret keys are not configured."
            return []
        self._ensure_client()
        if self._sdk_installed is False:
            return []
        try:
            handler = self.factory.create_callback_handler(self.config, trace_context)
        except ImportError as exc:
            self._sdk_installed = False
            self._last_error = str(exc)
            return []
        except Exception as exc:  # pragma: no cover - defensive SDK boundary
            self._last_error = str(exc)
            return []
        return [handler] if handler is not None else []

    def build_graph_config(
        self,
        base_config: dict[str, Any],
        trace_context: TraceContext,
        trace_metadata: TraceMetadata | None = None,
    ) -> dict[str, Any]:
        """Merge Langfuse callbacks/tags/metadata into a LangGraph config object."""

        graph_config = copy.deepcopy(base_config)
        callbacks = list(graph_config.get("callbacks", []))
        callbacks.extend(self.get_callbacks(trace_context))
        if callbacks:
            graph_config["callbacks"] = callbacks
        tags = list(dict.fromkeys([*graph_config.get("tags", []), "langgraph-agent-blueprint", trace_context.environment, *trace_context.tags]))
        graph_config["tags"] = [tag for tag in tags if tag]
        metadata = dict(graph_config.get("metadata", {}))
        metadata.update(
            {
                "session_id": trace_context.session_id,
                "thread_id": trace_context.thread_id,
                "environment": trace_context.environment,
                "release": trace_context.release,
                "langfuse_session_id": trace_context.session_id,
                "langfuse_user_id": trace_context.user_id,
                "langfuse_tags": graph_config["tags"],
            }
        )
        if trace_context.project_root:
            metadata["project_root"] = trace_context.project_root
        metadata.update(trace_context.metadata)
        if trace_metadata:
            metadata.update(trace_metadata.model_dump(mode="json", exclude_none=True))
        graph_config["metadata"] = self.mapper.redact(metadata)
        graph_config.setdefault("run_name", "lg-agent graph run")
        return graph_config

    def record_runtime_events(self, events: Iterable[RuntimeEvent | dict[str, Any]], trace_context: TraceContext) -> None:
        for item in events:
            self.record_runtime_event(item, trace_context)

    def record_runtime_event(self, event: RuntimeEvent | dict[str, Any], trace_context: TraceContext) -> None:
        if not self.is_enabled():
            return
        if not self._has_credentials():
            self._last_error = "Langfuse enabled but public/secret keys are not configured."
            return
        client = self._ensure_client()
        if client is None:
            return
        payload = self.mapper.map(event, trace_context)
        if payload is None:
            return
        try:
            self._emit_event(client, payload)
        except Exception as exc:  # pragma: no cover - defensive SDK boundary
            self._last_error = str(exc)

    def flush(self) -> None:
        if not self.is_enabled():
            return
        client = self._ensure_client()
        if client is None:
            return
        for method_name in ("flush", "shutdown"):
            method = getattr(client, method_name, None)
            if method is None:
                continue
            try:
                method()
            except Exception as exc:  # pragma: no cover - defensive SDK boundary
                self._last_error = str(exc)
            return

    def status(self) -> dict[str, Any]:
        if self.is_enabled() and not self._client_checked:
            self._ensure_client()
        sdk_installed = bool(self._sdk_installed) if self._sdk_installed is not None else None
        mode = "disabled"
        if self.is_enabled():
            mode = "callbacks_plus_runtime_events" if sdk_installed else "missing_dependency"
            if not self._has_credentials():
                mode = "config_error"
            if self._last_error and sdk_installed:
                mode = "degraded"
        return {
            "enabled": self.is_enabled(),
            "mode": mode,
            "sdk_installed": sdk_installed,
            "base_url_configured": bool(self.config.base_url),
            "public_key_present": bool(self.config.public_key),
            "secret_key_present": bool(self.config.secret_key),
            "environment": self.config.environment,
            "release": self.config.release,
            "capture_inputs": self.config.capture_inputs,
            "capture_outputs": self.config.capture_outputs,
            "auth_check": "not_run",
            "last_error": self._last_error,
        }

    def redact_payload(self, value: Any) -> Any:
        return self.mapper.redact(value)

    def _ensure_client(self) -> Any | None:
        if not self.is_enabled():
            return None
        if not self._has_credentials():
            self._last_error = "Langfuse enabled but public/secret keys are not configured."
            return None
        if self._client_checked:
            return self._client
        self._client_checked = True
        try:
            self._client = self.factory.create_client(self.config)
        except ImportError as exc:
            self._sdk_installed = False
            self._last_error = str(exc)
            self._client = None
        except Exception as exc:  # pragma: no cover - defensive SDK boundary
            self._sdk_installed = True
            self._last_error = str(exc)
            self._client = None
        else:
            self._sdk_installed = True
        return self._client

    def _has_credentials(self) -> bool:
        return bool(self.config.public_key and self.config.secret_key)

    @staticmethod
    def _emit_event(client: Any, payload: dict[str, Any]) -> None:
        if hasattr(client, "create_event"):
            client.create_event(**payload)
            return
        if hasattr(client, "start_as_current_observation"):
            with client.start_as_current_observation(as_type="event", **payload):
                return
        event_method = getattr(client, "event", None)
        if event_method is not None:
            event_method(**payload)


class NoopObservabilityService(ObservabilityService):
    """Explicit no-op implementation for tests and disabled deployments."""

    def __init__(self) -> None:
        super().__init__(LangfuseConfig(enabled=False))


class ObservabilityHook:
    """Lightweight hook adapter placeholder for future built-in hook registration."""

    def __init__(self, service: ObservabilityService) -> None:
        self.service = service
