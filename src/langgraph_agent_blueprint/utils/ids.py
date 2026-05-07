"""Utility module containing small reusable helpers used across the runtime."""

from __future__ import annotations

import re
from uuid import uuid4


RUNTIME_ID_PATTERN = r"^[A-Za-z0-9_-]{1,128}$"
RUNTIME_ID_RE = re.compile(RUNTIME_ID_PATTERN)


def new_id(prefix: str) -> str:
    """Create a stable readable identifier."""

    return f"{prefix}_{uuid4().hex[:16]}"


def validate_runtime_id(value: str, *, kind: str = "runtime id") -> str:
    """Validate user-supplied identifiers used as storage/checkpoint segments."""

    if not isinstance(value, str) or not RUNTIME_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid {kind}: expected 1-128 ASCII letters, digits, '_' or '-'")
    return value


def validate_session_id(value: str) -> str:
    """Validate a session id before using it as an external/runtime identifier."""

    return validate_runtime_id(value, kind="session_id")


def validate_thread_id(value: str) -> str:
    """Validate a thread id before using it as an external/runtime identifier."""

    return validate_runtime_id(value, kind="thread_id")

