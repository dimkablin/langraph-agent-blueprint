from __future__ import annotations

import subprocess
from pathlib import Path


def run_subprocess(command: list[str] | str, cwd: Path, timeout: float, shell: bool) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with text capture."""

    return subprocess.run(
        command,
        cwd=str(cwd),
        timeout=timeout,
        shell=shell,
        text=True,
        capture_output=True,
    )

