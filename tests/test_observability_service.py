"""ObservabilityService callback and status coverage."""

from __future__ import annotations

from langgraph_agent_blueprint.models.observability import LangfuseConfig, TraceContext, TraceMetadata
from langgraph_agent_blueprint.services.observability_service import ObservabilityService


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.flushed = False

    def create_event(self, **kwargs):
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

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
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

    def create_client(self, config: LangfuseConfig):
        return self.client

    def create_callback_handler(self, config: LangfuseConfig, trace_context: TraceContext):
        self.callbacks_created += 1
        self.last_callback_config = (config, trace_context)
        return RecordingCallbackHandler(trace_context.session_id)


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

    graph_config = service.build_graph_config({"configurable": {"thread_id": "thread-1"}}, context, metadata)

    assert graph_config["configurable"]["thread_id"] == "thread-1"
    assert graph_config["callbacks"][0].session_id == "session-1"
    assert graph_config["metadata"]["session_id"] == "session-1"
    assert graph_config["metadata"]["provider"] == "fake"
    assert "langgraph-agent-blueprint" in graph_config["tags"]
    assert "ci" in graph_config["tags"]
    assert factory.callbacks_created == 1
