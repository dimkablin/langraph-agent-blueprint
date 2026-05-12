"""Local OS folder picker used by the workspace API in desktop/local runs."""

from __future__ import annotations

from pathlib import Path


class FolderPickerUnavailableError(RuntimeError):
    """Raised when the runtime cannot open a local folder picker."""


class FolderPickerService:
    """Thin boundary around the OS folder picker.

    The selected path still goes through WorkspaceService validation before it
    becomes an active workspace.
    """

    def select_directory(self, *, title: str) -> Path | None:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:  # pragma: no cover - depends on host UI packages
            raise FolderPickerUnavailableError("Folder picker is unavailable in this environment.") from exc

        root = tk.Tk()
        try:
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory(parent=root, title=title, mustexist=True)
        finally:
            root.destroy()

        if not selected:
            return None
        return Path(selected)
