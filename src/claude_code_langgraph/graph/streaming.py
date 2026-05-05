from __future__ import annotations

import json
from typing import Any, Iterable


def iter_new_events(previous_count: int, state: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield graph events added after a previous offset."""

    yield from state.get("ui_events", [])[previous_count:]


def events_as_json_lines(events: Iterable[dict[str, Any]]) -> Iterable[str]:
    for item in events:
        yield json.dumps(item, ensure_ascii=False)

