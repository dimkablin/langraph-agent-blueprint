"""Package marker for langgraph_agent_blueprint.graph and its public runtime components."""

from .state import AssistantState, create_initial_state

__all__ = ["AssistantGraphRuntime", "AssistantState", "build_main_graph", "create_initial_state"]


def __getattr__(name: str):
    """Load builder exports lazily to avoid service/dependency import cycles."""

    if name in {"AssistantGraphRuntime", "build_main_graph"}:
        from .builder import AssistantGraphRuntime, build_main_graph

        return {"AssistantGraphRuntime": AssistantGraphRuntime, "build_main_graph": build_main_graph}[name]
    raise AttributeError(name)
