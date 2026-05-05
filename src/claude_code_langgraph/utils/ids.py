from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    """Create a stable readable identifier."""

    return f"{prefix}_{uuid4().hex[:16]}"

