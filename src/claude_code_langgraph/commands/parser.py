from __future__ import annotations


def parse_slash_command(text: str) -> tuple[str, str] | None:
    """Parse `/name args` into command name and argument string."""

    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped[1:].split(maxsplit=1)
    name = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return name, args

