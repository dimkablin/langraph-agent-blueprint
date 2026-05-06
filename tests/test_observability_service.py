"""ObservabilityService callback and status coverage."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from langgraph_agent_blueprint.models.observability import LangfuseConfig, TraceContext, TraceMetadata
from langgraph_agent_blueprint.services.observability_service import ObservabilityService


class RecordingObservation:
    def __init__(self, client: "RecordingLangfuseClient", record: dict[str, Any]) -> None:
        self.client = client
        self.record = record

    def update(self, *args, **kwargs) -> None:
        payload = dict(args[0]) if args and isinstance(args[0], dict) else {}
        payload.update(kwargs)
        self.record.setdefault("updates", []).append(payload)
        if "metadata" in payload and isinstance(payload["metadata"], dict):
            self.record.setdefault("metadata", {}).update(payload["metadata"])
        if "output" in payload:
            self.record["output"] = payload["output"]
        self.client.metadata_updates.append({"trace_id": self.record.get("trace_id"), **payload})

    def set_trace_io(self, **kwargs) -> None:
        self.update(**kwargs)


class RecordingObservationContext(AbstractContextManager):
    def __init__(self, client: "RecordingLangfuseClient", as_type: str, name: str | None, payload: dict[str, Any]) -> None:
        self.client = client
        self.as_type = as_type
        self.name = name or payload.get("name") or "observation"
        self.payload = payload
        self.record: dict[str, Any] | None = None

    def __enter__(self) -> RecordingObservation:
        propagated = self.client.current_propagated()
        if self.client.current_trace_id is None:
            trace_id = f"trace-{len(self.client.top_level_traces) + 1}"
            metadata = dict(self.payload.get("metadata") or {})
            metadata.update(propagated.get("metadata") or {})
            self.record = {
                "trace_id": trace_id,
                "name": self.name,
                "as_type": self.as_type,
                "input": self.payload.get("input"),
                "metadata": metadata,
                "session_id": propagated.get("session_id") or metadata.get("session_id"),
                "user_id": propagated.get("user_id"),
                "tags": propagated.get("tags") or [],
                "updates": [],
            }
            self.client.top_level_traces.append(self.record)
        else:
            self.record = {
                "trace_id": self.client.current_trace_id,
                "parent_trace_id": self.client.current_trace_id,
                "name": self.name,
                "as_type": self.as_type,
                "input": self.payload.get("input"),
                "output": self.payload.get("output"),
                "metadata": dict(self.payload.get("metadata") or {}),
                "level": self.payload.get("level"),
                "status_message": self.payload.get("status_message"),
                "active_context": True,
            }
            self.client.child_observations.append(self.record)
        self.client._active_stack.append(self.record)
        return RecordingObservation(self.client, self.record)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.client._active_stack:
            self.client._active_stack.pop()


class RecordingPropagationContext(AbstractContextManager):
    def __init__(self, client: "RecordingLangfuseClient", payload: dict[str, Any]) -> None:
        self.client = client
        self.payload = payload

    def __enter__(self):
        self.client._propagated_stack.append(self.payload)
        trace = self.client.current_trace()
        if trace is not None:
            trace["session_id"] = self.payload.get("session_id") or trace.get("session_id")
            trace["user_id"] = self.payload.get("user_id") or trace.get("user_id")
            trace["tags"] = self.payload.get("tags") or trace.get("tags", [])
            trace.setdefault("metadata", {}).update(self.payload.get("metadata") or {})
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.client._propagated_stack:
            self.client._propagated_stack.pop()


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.top_level_traces: list[dict] = []
        self.child_observations: list[dict] = []
        self.unscoped_events: list[dict] = []
        self.metadata_updates: list[dict] = []
        self.flushed = False
        self._active_stack: list[dict] = []
        self._propagated_stack: list[dict] = []

    @property
    def current_trace_id(self) -> str | None:
        if not self._active_stack:
            return None
        return self._active_stack[0].get("trace_id")

    def current_trace(self) -> dict | None:
        if not self._active_stack:
            return None
        return self._active_stack[0]

    def current_propagated(self) -> dict:
        merged: dict[str, Any] = {}
        for payload in self._propagated_stack:
            merged.update(payload)
            if "metadata" in payload:
                merged["metadata"] = {**merged.get("metadata", {}), **payload["metadata"]}
        return merged

    def start_as_current_observation(self, as_type: str = "span", name: str | None = None, **kwargs):
        return RecordingObservationContext(self, as_type, name, kwargs)

    def propagate_attributes(self, **kwargs):
        return RecordingPropagationContext(self, kwargs)

    def create_event(self, **kwargs):
        if self.current_trace_id is None:
            self.unscoped_events.append(kwargs)
        else:
            kwargs["parent_trace_id"] = self.current_trace_id
            self.child_observations.append(kwargs)
        self.events.append(kwargs)
        return kwargs

    def flush(self) -> None:
        self.flushed = True


class RecordingCallbackHandler:
    ignore_chain = False
    ignore_llm = False
    ignore_chat_model = False
    ignore_agent = False
    ignore_retriever = False
    ignore_tool = False
    ignore_retry = False
    raise_error = False

    def __init__(self, session_id: str, active_trace_id: str | None = None) -> None:
        self.session_id = session_id
        self.active_trace_id = active_trace_id
        self.calls: list[str] = []

    def __getattr__(self, name: str):
        if name.startswith("on_"):
            def callback(*args, **kwargs):
                self.calls.append(name)

            return callback
        raise AttributeError(name)


class RecordingLangfuseFactory:
    def __init__(self) -> None:
        self.client = RecordingLangfuseClient()
        self.callbacks_created = 0
        self.last_callback_config = None
        self.handlers: list[RecordingCallbackHandler] = []

    def create_client(self, config: LangfuseConfig):
        return self.client

    def create_callback_handler(self, config: LangfuseConfig, trace_context: TraceContext):
        self.callbacks_created += 1
        self.last_callback_config = (config, trace_context)
        handler = RecordingCallbackHandler(trace_context.session_id, self.client.current_trace_id)
        self.handlers.append(handler)
        return handler


class MissingLangfuseFactory:
    def create_client(self, config: LangfuseConfig):
        raise ImportError("langfuse is not installed")

    def create_callback_handler(self, config: LangfuseConfig, trace_context: TraceContext):
        raise ImportError("langfuse is not installed")


def test_disabled_observability_is_noop() -> None:
    service = ObservabilityService(LangfuseConfig(enabled=False))
    context = TraceContext(session_id="session-1")

    assert service.is_enabled() is False
    assert service.get_callbacks(context) == []
    assert service.status()["mode"] == "disabled"


def test_enabled_missing_dependency_reports_status_without_crashing() -> None:
    service = ObservabilityService(
        LangfuseConfig(enabled=True, public_key="pk", secret_key="sk", base_url="https://langfuse.example"),
        factory=MissingLangfuseFactory(),
    )
    context = TraceContext(session_id="session-1")

    assert service.get_callbacks(context) == []
    status = service.status()
    assert status["enabled"] is True
    assert status["sdk_installed"] is False
    assert status["mode"] == "missing_dependency"
    assert "sk" not in str(status)


def test_graph_config_preserves_configurable_and_adds_callbacks_metadata_tags() -> None:
    factory = RecordingLangfuseFactory()
    service = ObservabilityService(
        LangfuseConfig(
            enabled=True,
            public_key="pk",
            secret_key="sk",
            base_url="https://langfuse.example",
            environment="ci",
            release="test",
        ),
        factory=factory,
    )
    context = TraceContext(session_id="session-1", thread_id="thread-1", environment="ci")
    metadata = TraceMetadata(provider="fake", model="fake-model", permission_mode="default")

    with service.trace_turn(context, metadata, input_data={"message": "hello"}) as turn:
        graph_config = turn.graph_config({"configurable": {"thread_id": "thread-1"}})

    assert graph_config["configurable"]["thread_id"] == "thread-1"
    assert graph_config["callbacks"][0].session_id == "session-1"
    assert graph_config["callbacks"][0].active_trace_id == "trace-1"
    assert graph_config["metadata"]["session_id"] == "session-1"
    assert graph_config["metadata"]["provider"] == "fake"
    assert "langgraph-agent-blueprint" in graph_config["tags"]
    assert "ci" in graph_config["tags"]
    assert factory.callbacks_created == 1
    assert len(factory.client.top_level_traces) == 1
    assert factory.client.top_level_traces[0]["session_id"] == "session-1"
