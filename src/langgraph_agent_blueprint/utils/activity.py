"""Sanitization and naming helpers for public agent activity payloads."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


MAX_ACTIVITY_TEXT_CHARS = 500
MAX_ACTIVITY_SUMMARY_CHARS = 240
MAX_ACTIVITY_LIST_ITEMS = 30
REDACTED_VALUE = "***"
TRUNCATED_SUFFIX = "...<truncated>"

SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}

_NAMESPACE_RE = re.compile(r"[^a-z0-9]+")
_ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|auth|credential|credentials|password|secret|token)\b(\s*[:=]\s*)([^\s;&]+)"
)
_FLAG_SECRET_RE = re.compile(
    r"(?i)(--(?:api[_-]?key|authorization|auth|credential|credentials|password|secret|token)\s+)([^\s;&]+)"
)


def normalize_activity_namespace(value: Any) -> str:
    """Return a safe lowercase namespace segment for producer-owned event types."""

    normalized = _NAMESPACE_RE.sub("_", str(value or "").strip().lower()).strip("_")
    return normalized or "unknown"


def safe_activity_data(data: dict[str, Any], *, max_text_chars: int = MAX_ACTIVITY_TEXT_CHARS) -> dict[str, Any]:
    """Return JSON-like activity data with sensitive values redacted and long values bounded."""

    sanitized = _sanitize_value(data, max_text_chars=max_text_chars)
    return sanitized if isinstance(sanitized, dict) else {}


def bounded_activity_text(value: Any, *, limit: int = MAX_ACTIVITY_TEXT_CHARS) -> str:
    """Render, redact, and bound text for public activity summaries."""

    text = redact_activity_text(str(value or ""))
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(TRUNCATED_SUFFIX))] + TRUNCATED_SUFFIX


def activity_text_summary(value: Any, *, limit: int = MAX_ACTIVITY_SUMMARY_CHARS) -> str | None:
    text = bounded_activity_text(value, limit=limit).strip()
    return text or None


def redact_activity_text(value: str) -> str:
    """Redact common inline secret shapes in commands, stderr, stdout, and summaries."""

    text = _ASSIGNMENT_SECRET_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED_VALUE}", value)
    return _FLAG_SECRET_RE.sub(lambda match: f"{match.group(1)}{REDACTED_VALUE}", text)


def safe_display_path(path: Any, root: Path | None = None) -> str:
    """Prefer project-relative display paths for activity refs and data."""

    text = str(path or "")
    if not text:
        return ""
    candidate = Path(text)
    if root is not None:
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            pass
    return candidate.as_posix()


def _sanitize_value(value: Any, *, max_text_chars: int) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                sanitized[key_text] = REDACTED_VALUE
            else:
                sanitized[key_text] = _sanitize_value(item, max_text_chars=max_text_chars)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        sanitized_items = [_sanitize_value(item, max_text_chars=max_text_chars) for item in items[:MAX_ACTIVITY_LIST_ITEMS]]
        if len(items) > MAX_ACTIVITY_LIST_ITEMS:
            sanitized_items.append(TRUNCATED_SUFFIX)
        return sanitized_items
    if isinstance(value, str):
        return bounded_activity_text(value, limit=max_text_chars)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return bounded_activity_text(value, limit=max_text_chars)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)
