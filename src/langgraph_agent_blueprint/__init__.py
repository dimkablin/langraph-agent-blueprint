"""Python/LangGraph Claude Code-like assistant runtime."""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)
try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
except ImportError:  # pragma: no cover - optional dependency shape
    LangChainPendingDeprecationWarning = Warning  # type: ignore[assignment]
warnings.filterwarnings(
    "ignore",
    message=".*allowed_objects.*will change.*",
    category=LangChainPendingDeprecationWarning,
)

__version__ = "0.1.0"
