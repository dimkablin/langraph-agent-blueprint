from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver


def default_checkpointer() -> InMemorySaver:
    """Return the default in-memory checkpointer used for interrupt/resume."""

    return InMemorySaver()

