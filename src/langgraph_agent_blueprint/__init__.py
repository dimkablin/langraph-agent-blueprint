"""Python/LangGraph Claude Code-like assistant runtime."""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)

__version__ = "0.1.0"
