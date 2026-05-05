from __future__ import annotations

from .event_renderer import render_event


def render_events(events: list[dict]) -> str:
    return "\n".join(render_event(event) for event in events)

