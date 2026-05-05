"""LangGraph node module responsible for one thin state-transition step in the assistant runtime."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from claude_code_langgraph.dependencies import AppDependencies
from claude_code_langgraph.models.messages import event


def finalize_response_node(state: dict, deps: AppDependencies) -> dict:
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
    return {"final_response": final, "metadata": metadata, "ui_events": [event("final_response", content=final)]}

