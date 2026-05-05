from __future__ import annotations


def render_event(event: dict) -> str:
    """Render one graph event for terminal output."""

    event_type = event.get("type", "event")
    data = event.get("data", {})
    if event_type == "model_token":
        return str(data.get("token", ""))
    if event_type == "permission_required":
        return f"Permission required: {data.get('tool_name')}"
    if event_type == "final_response":
        return str(data.get("content", ""))
    return f"[{event_type}] {data}"

