"""Service-layer module that implements concrete operations behind graph nodes and tools."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from claude_code_langgraph.utils.text import render_messages


class ExportResult(BaseModel):
    """Structured result for transcript export operations."""
    path: Path
    text: str


class ExportService:
    """Transcript/report export service."""

    def __init__(self, export_root: str | Path) -> None:
        self.export_root = Path(export_root)

    def export_transcript(self, session_id: str, messages: list[BaseMessage], format: str = "markdown") -> ExportResult:
        suffix = "md" if format == "markdown" else "txt"
        text = render_messages(messages)
        target = self.export_root / "exports" / f"{session_id}.{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return ExportResult(path=target, text=text)

