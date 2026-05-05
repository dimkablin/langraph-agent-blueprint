"""Pytest fixtures and test-run isolation helpers for the assistant runtime suite."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    """Workspace-local temp path to avoid restricted system temp ACLs in this sandbox."""

    root = Path.cwd() / "test_runs"
    root.mkdir(exist_ok=True)
    path = root / uuid4().hex
    path.mkdir()
    return path

