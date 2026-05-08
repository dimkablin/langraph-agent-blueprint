"""Optional Langfuse observability integration for graph runs and RuntimeEvents."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable
from contextlib import nullcontext
from pathlib import PurePosixPath, PureWindowsPath
import re
from types import TracebackType
from typing import Any

from pydantic import ValidationError

from langgraph_agent_blueprint.models import LangfuseConfig, ObservabilityEvent, RuntimeEvent, TraceContext, TraceMetadata


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
HIGH_SIGNAL_RUNTIME_EVENTS = {
    "tool_call_started",
    "tool_call_finished",
    "tool_call_error",
    "permission_required",
    "permission_resolved",
    "skill_started",
    "skill_finished",
    "hook_blocked",
    "hook_error",
    "mcp_tool_call_started",
    "mcp_tool_call_finished",
    "mcp_tool_call_error",
    "context_resolution_error",
    "subagent_started",
    "subagent_finished",
    "subagent_error",
    "subagent_cancelled",
    "subagent_timeout",
    "final_response",
    "error",
}
LOW_SIGNAL_RUNTIME_EVENTS = {
    "session_started",
    "command_started",
    "command_finished",
    "model_message",
    "hook_started",
    "hook_finished",
    "mcp_server_connected",
    "mcp_tools_discovered",
    "mcp_resources_discovered",
    "mcp_prompts_discovered",
    "context_resolution_started",
    "context_fragment_added",
    "context_budget_applied",
    "subagent_event",
    "compact_started",
    "compact_finished",
    "session_persisted",
}
IMPORTANT_RUNTIME_EVENTS = HIGH_SIGNAL_RUNTIME_EVENTS | LOW_SIGNAL_RUNTIME_EVENTS
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_USER_PATH_RE = re.compile(r"^[A-Za-z]:[\\/](Users|Documents)[\\/]", re.IGNORECASE)
POSIX_PRIVATE_PATH_PREFIXES = ("/home/", "/Users/", "/var/", "/tmp/", "/opt/", "/srv/", "/workspace/", "/mnt/", "/root/")


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
        if isinstance(value, str):
            return self._sanitize_path(value, key)
        return value

    def _sanitize_path(self, value: str, key: str | None = None) -> Any:
        if self.config.include_project_paths:
            return value
        if not self._looks_like_private_path(value, key):
            return value
        normalized = value.rstrip("\\/")
        if "\\" in normalized or WINDOWS_ABSOLUTE_PATH_RE.match(normalized):
            basename = PureWindowsPath(normalized).name
        else:
            basename = PurePosixPath(normalized).name
        return {
            "basename": basename or "<root>",
            "path_hash": hashlib.sha256(value.encode("utf-8")).hexdigest()[:12],
        }

    @staticmethod
    def _looks_like_private_path(value: str, key: str | None = None) -> bool:
        if not value or "://" in value:
            return False
        key_text = (key or "").lower()
        path_key = any(part in key_text for part in ("path", "root", "cwd", "directory", "dir", "file"))
        if WINDOWS_ABSOLUTE_PATH_RE.match(value) or value.startswith("\\\\"):
            return path_key or bool(WINDOWS_USER_PATH_RE.match(value)) or "\\Users\\" in value or "\\Documents\\" in value
        if value.startswith(POSIX_PRIVATE_PATH_PREFIXES):
            return True
        return path_key and value.startswith("/")

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
        self._unscoped_event_warning_emitted = False

    @property
    def client_events(self) -> list[dict[str, Any]]:
        client = self._client
        child_observations = getattr(client, "child_observations", None)
        if isinstance(child_observations, list):
            return child_observations
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

    def trace_turn(
        self,
        trace_context: TraceContext,
        trace_metadata: TraceMetadata | None = None,
        *,
        input_data: Any | None = None,
        name: str = "lg-agent graph run",
    ) -> "ScopedObservabilityTurn":
        """Open one Langfuse root observation for one user/runtime turn."""

        return ScopedObservabilityTurn(self, trace_context, trace_metadata, input_data=input_data, name=name)

    def record_runtime_events(self, events: Iterable[RuntimeEvent | dict[str, Any]], trace_context: TraceContext) -> None:
        for item in events:
            self.record_runtime_event(item, trace_context)

    def record_runtime_event(self, event: RuntimeEvent | dict[str, Any], trace_context: TraceContext) -> None:
        """Skip unscoped RuntimeEvent export.

        Production graph runs call this through ``ScopedObservabilityTurn``. Calling it
        directly must not create top-level Langfuse traces for runtime.* events.
        """

        if not self.is_enabled():
            return
        if not self._has_credentials():
            self._last_error = "Langfuse enabled but public/secret keys are not configured."
            return
        if not self._unscoped_event_warning_emitted:
            self._last_error = "RuntimeEvent export skipped because no active Langfuse trace context is open."
            self._unscoped_event_warning_emitted = True

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
            "runtime_events_mode": self.config.runtime_events_mode,
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

    def _record_runtime_event_scoped(
        self,
        event: RuntimeEvent | dict[str, Any],
        trace_context: TraceContext,
        turn: "ScopedObservabilityTurn",
    ) -> None:
        if not self.is_enabled() or self.config.runtime_events_mode == "off":
            return
        payload = self.mapper.map(event, trace_context)
        if payload is None:
            return
        event_type = payload.get("metadata", {}).get("runtime_event_type")
        if self.config.runtime_events_mode == "metadata_only":
            turn.add_timeline_event(payload)
            return
        if self.config.runtime_events_mode == "high_signal" and event_type not in HIGH_SIGNAL_RUNTIME_EVENTS:
            turn.add_timeline_event(payload)
            return
        turn.emit_child_observation(payload)


class ScopedObservabilityTurn:
    """Trace-scoped facade used by graph runtime for one user turn."""

    def __init__(
        self,
        service: ObservabilityService,
        trace_context: TraceContext,
        trace_metadata: TraceMetadata | None = None,
        *,
        input_data: Any | None = None,
        name: str = "lg-agent graph run",
    ) -> None:
        self.service = service
        self.trace_context = trace_context
        self.trace_metadata = trace_metadata
        self.input_data = input_data
        self.name = name
        self.client: Any | None = None
        self.root_observation: Any | None = None
        self._observation_cm: Any | None = None
        self._propagation_cm: Any | None = None
        self._active = False
        self._timeline: list[dict[str, Any]] = []
        self._output_set = False
        self._output: Any | None = None

    def __enter__(self) -> "ScopedObservabilityTurn":
        if not self.service.is_enabled():
            return self
        if not self.service._has_credentials():
            self.service._last_error = "Langfuse enabled but public/secret keys are not configured."
            return self
        self.client = self.service._ensure_client()
        if self.client is None:
            return self
        self._observation_cm = self._start_root_observation()
        try:
            self.root_observation = self._observation_cm.__enter__()
        except Exception as exc:  # pragma: no cover - defensive SDK boundary
            self.service._last_error = str(exc)
            self._observation_cm = None
            return self
        self._active = self.root_observation is not None
        self._propagation_cm = self._propagation_context()
        try:
            self._propagation_cm.__enter__()
        except Exception as exc:  # pragma: no cover - defensive SDK boundary
            self.service._last_error = str(exc)
            self._propagation_cm = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc is not None:
            self.set_output({"error": str(exc)})
        if self._timeline:
            self._update_root(metadata={"runtime_timeline": self._timeline[-100:]})
        if self._output_set:
            self._update_root(output=self._output)
        for context_manager in (self._propagation_cm, self._observation_cm):
            if context_manager is None:
                continue
            try:
                context_manager.__exit__(exc_type, exc, traceback)
            except Exception as close_exc:  # pragma: no cover - defensive SDK boundary
                self.service._last_error = str(close_exc)
        self._active = False
        self.service.flush()

    def graph_config(self, base_config: dict[str, Any], trace_metadata: TraceMetadata | None = None) -> dict[str, Any]:
        return self.service.build_graph_config(base_config, self.trace_context, trace_metadata or self.trace_metadata)

    def record_runtime_events(self, events: Iterable[RuntimeEvent | dict[str, Any]], trace_context: TraceContext | None = None) -> None:
        for item in events:
            self.record_runtime_event(item, trace_context)

    def record_runtime_event(self, event: RuntimeEvent | dict[str, Any], trace_context: TraceContext | None = None) -> None:
        self.service._record_runtime_event_scoped(event, trace_context or self.trace_context, self)

    def emit_child_observation(self, payload: dict[str, Any]) -> None:
        if not self._active or self.client is None:
            self.add_timeline_event(payload)
            return
        try:
            with self.client.start_as_current_observation(as_type="span", **payload):
                return
        except AttributeError:
            self.add_timeline_event(payload)
        except Exception as exc:  # pragma: no cover - defensive SDK boundary
            self.service._last_error = str(exc)
            self.add_timeline_event(payload)

    def add_timeline_event(self, payload: dict[str, Any]) -> None:
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        self._timeline.append(
            self.service.mapper.redact(
                {
                    "name": payload.get("name"),
                    "runtime_event_type": metadata.get("runtime_event_type"),
                    "level": payload.get("level"),
                    "status_message": payload.get("status_message"),
                    "node": metadata.get("node"),
                }
            )
        )

    def set_output(self, output: Any) -> None:
        if output is None:
            return
        self._output = self.service.mapper.redact(output if self.service.config.capture_outputs else "<redacted>")
        self._output_set = True

    def _start_root_observation(self) -> Any:
        if self.client is None or not hasattr(self.client, "start_as_current_observation"):
            return nullcontext(None)
        payload = {
            "as_type": "span",
            "name": self.name,
            "input": self.service.mapper.redact(self.input_data if self.service.config.capture_inputs else "<redacted>"),
            "metadata": self._base_metadata(),
        }
        for candidate in (
            payload,
            {key: value for key, value in payload.items() if key != "metadata"},
            {"as_type": "span", "name": self.name},
        ):
            try:
                return self.client.start_as_current_observation(**candidate)
            except TypeError:
                continue
            except Exception as exc:  # pragma: no cover - defensive SDK boundary
                self.service._last_error = str(exc)
                return nullcontext(None)
        return nullcontext(None)

    def _propagation_context(self) -> Any:
        if self.client is None:
            return nullcontext()
        kwargs = {
            "session_id": self.trace_context.session_id,
            "user_id": self.trace_context.user_id,
            "tags": self._tags(),
            "metadata": self._propagation_metadata(),
            "version": self.trace_context.release,
        }
        clean = {key: value for key, value in kwargs.items() if value not in (None, [], {})}
        method = getattr(self.client, "propagate_attributes", None)
        if method is not None:
            try:
                return method(**clean)
            except TypeError:
                return method()
        try:
            from langfuse import propagate_attributes
        except ImportError:
            return nullcontext()
        try:
            return propagate_attributes(**clean)
        except TypeError:
            return nullcontext()

    def _base_metadata(self) -> dict[str, Any]:
        metadata = {
            "session_id": self.trace_context.session_id,
            "thread_id": self.trace_context.thread_id,
            "environment": self.trace_context.environment,
            "release": self.trace_context.release,
            **self.trace_context.metadata,
        }
        if self.trace_context.project_root:
            metadata["project_root"] = self.trace_context.project_root
        if self.trace_metadata:
            metadata.update(self.trace_metadata.model_dump(mode="json", exclude_none=True))
        return self.service.mapper.redact(metadata)

    def _propagation_metadata(self) -> dict[str, str]:
        metadata = self._base_metadata()
        return {
            key: self._stringify_propagation_value(value, limit=200)
            for key, value in metadata.items()
            if value not in (None, "", [], {})
        }

    def _stringify_propagation_value(self, value: Any, *, limit: int = 200) -> str:
        if isinstance(value, str):
            text = value
        elif isinstance(value, bool):
            text = "true" if value else "false"
        elif isinstance(value, (int, float)):
            text = str(value)
        else:
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        if len(text) > limit:
            suffix = "...[truncated]"
            return text[: max(0, limit - len(suffix))] + suffix
        return text

    def _tags(self) -> list[str]:
        return [
            tag
            for tag in dict.fromkeys(["langgraph-agent-blueprint", self.trace_context.environment, *self.trace_context.tags])
            if tag
        ]

    def _update_root(self, **payload: Any) -> None:
        clean = {key: self.service.mapper.redact(value) for key, value in payload.items() if value is not None}
        if not clean:
            return
        target = self.root_observation
        update = getattr(target, "update", None)
        if update is not None:
            try:
                update(**clean)
                return
            except TypeError:
                try:
                    update(clean)
                    return
                except TypeError:
                    pass
        if self.client is None:
            return
        for method_name in ("update_current_span", "update_current_observation", "set_current_trace_io"):
            method = getattr(self.client, method_name, None)
            if method is None:
                continue
            try:
                method(**clean)
                return
            except TypeError:
                try:
                    method(clean)
                    return
                except TypeError:
                    continue


class NoopObservabilityService(ObservabilityService):
    """Explicit no-op implementation for tests and disabled deployments."""

    def __init__(self) -> None:
        super().__init__(LangfuseConfig(enabled=False))


class ObservabilityHook:
    """Lightweight hook adapter placeholder for future built-in hook registration."""

    def __init__(self, service: ObservabilityService) -> None:
        self.service = service
