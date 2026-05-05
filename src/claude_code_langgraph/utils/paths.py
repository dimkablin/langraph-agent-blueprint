from __future__ import annotations

from pathlib import Path


def resolve_under_root(path: str | Path, root: str | Path) -> Path:
    """Resolve a path and reject traversal outside root."""

    root_path = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise PermissionError(f"Path is outside allowed root: {resolved}") from exc
    return resolved


def ensure_dir(path: str | Path) -> Path:
    """Create a directory and return it as a Path."""

    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target

