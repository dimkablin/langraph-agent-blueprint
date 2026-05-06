"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .file_service import FileService


class NotebookService:
    """Jupyter notebook read/edit support backed by JSON file operations."""

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def read(self, path: str | Path) -> dict[str, Any]:
        notebook = self.file_service.read_notebook(path)
        cells = []
        for idx, cell in enumerate(notebook.get("cells", [])):
            cells.append({"index": idx, "cell_type": cell.get("cell_type"), "source": "".join(cell.get("source", []))})
        return {"path": str(self.file_service.resolve(path)), "cells": cells, "metadata": notebook.get("metadata", {})}

    def edit_cell(self, path: str | Path, index: int, source: str) -> dict[str, Any]:
        notebook = self.file_service.read_notebook(path)
        cells = notebook.setdefault("cells", [])
        if index < 0 or index >= len(cells):
            raise IndexError("Notebook cell index out of range")
        cells[index]["source"] = source.splitlines(keepends=True)
        self.file_service.write_notebook(path, notebook)
        return {"path": str(self.file_service.resolve(path)), "index": index, "source": source}

