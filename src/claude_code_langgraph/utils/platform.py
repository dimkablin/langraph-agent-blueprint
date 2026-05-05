from __future__ import annotations

import os
import sys


def is_windows() -> bool:
    """Return whether the current runtime is Windows."""

    return os.name == "nt" or sys.platform.startswith("win")

