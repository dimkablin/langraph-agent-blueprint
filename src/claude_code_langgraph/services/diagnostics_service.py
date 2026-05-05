from __future__ import annotations

import shutil
import sys
from typing import Any


class DiagnosticsService:
    """Environment health checks for /doctor and DiagnosticsTool."""

    def run(self) -> dict[str, Any]:
        return {
            "python": sys.version,
            "ripgrep": bool(shutil.which("rg")),
            "status": "ok",
            "limitations": ["IDE/LSP integration is architectural/minimal in this port."],
        }

