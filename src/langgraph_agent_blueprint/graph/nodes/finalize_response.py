"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from langgraph_agent_blueprint.dependencies import AppDependencies
from langgraph_agent_blueprint.models import AgentActivityEvent, AgentActivitySource, AssistantFinalStreamEvent, event, stream_event_payload
from langgraph_agent_blueprint.utils.ids import new_id


def finalize_response_node(state: dict, deps: AppDependencies) -> dict:
    """Choose the user-visible final response from explicit output, tool results, or AI messages."""

    final = state.get("final_response")
    if not final:
        for result in reversed(state.get("tool_results", [])):
            final = f"Tool {result.get('name')} {result.get('status')}: {result.get('content', '')}"
            break
    if not final:
        for message in reversed(state.get("messages", [])):
            if isinstance(message, AIMessage):
                final = str(message.content)
                break
    final = final or ""
    metadata = {**state.get("metadata", {}), "graph_finished": True}
    if metadata.get("compact_route") == "compact" and not final:
        return {"final_response": final, "metadata": metadata, "ui_events": []}
    activity = AgentActivityEvent(
        type="runtime.run.completed",
        source=AgentActivitySource(kind="runtime", component="AssistantGraphRuntime"),
        category="runtime",
        status="success",
        title="Run completed",
    )
    message_id = str(metadata.get("assistant_message_id") or new_id("assistant"))
    return {
        "final_response": final,
        "metadata": metadata,
        "ui_events": [
            event(
                "final_response",
                content=final,
                activity=activity.model_dump(mode="json"),
                stream_event=stream_event_payload(AssistantFinalStreamEvent(message_id=message_id, content=final)),
            )
        ],
    }

