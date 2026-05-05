from __future__ import annotations

import hashlib
from pathlib import Path


def project_hash(project_root: str | Path) -> str:
    """Hash a project path for storage layout stability."""

    return hashlib.sha256(str(Path(project_root).resolve()).encode("utf-8")).hexdigest()[:16]


def project_storage_dir(storage_dir: str | Path, project_root: str | Path) -> Path:
    """Return storage directory for a project."""

    return Path(storage_dir) / "projects" / project_hash(project_root)

