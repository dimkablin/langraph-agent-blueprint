"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel

from langgraph_agent_blueprint.models import ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services import FileService, NotebookService

from .base import BaseTool, ToolExecutionContext, ToolOutput


class NotebookReadInput(BaseModel):
    """Pydantic input schema for the notebook read operation."""
    path: str


class NotebookReadOutput(ToolOutput):
    """Pydantic output schema for the notebook read operation."""
    cells: list[dict[str, object]]


class NotebookReadTool(BaseTool[NotebookReadInput, NotebookReadOutput]):
    """Model-callable tool that reads Jupyter notebook cells and metadata."""
    name = "notebook_read"
    description = "Read Jupyter notebook cells and metadata."
    input_schema = NotebookReadInput
    output_schema = NotebookReadOutput
    permission = ToolPermissionMetadata(action="read", risk="low", is_read_only=True, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="notebook")

    def __init__(self, notebook_service: NotebookService) -> None:
        self.notebook_service = notebook_service

    def run(self, data: NotebookReadInput, context: ToolExecutionContext) -> NotebookReadOutput:
        result = _notebook_service_for_context(self.notebook_service, context).read(data.path)
        return NotebookReadOutput(content=f"Read notebook {result['path']}", cells=result["cells"], metadata=result)


class NotebookEditInput(BaseModel):
    """Pydantic input schema for the notebook edit operation."""
    path: str
    index: int
    source: str


class NotebookEditOutput(ToolOutput):
    """Pydantic output schema for the notebook edit operation."""
    path: str
    index: int


class NotebookEditTool(BaseTool[NotebookEditInput, NotebookEditOutput]):
    """Model-callable tool that edits a Jupyter notebook cell after approval."""
    name = "notebook_edit"
    description = "Edit a Jupyter notebook cell."
    input_schema = NotebookEditInput
    output_schema = NotebookEditOutput
    permission = ToolPermissionMetadata(action="edit", risk="medium", requires_permission=True, reason="This tool edits a notebook file.")
    runtime = ToolRuntimeMetadata(kind="notebook")

    def __init__(self, notebook_service: NotebookService) -> None:
        self.notebook_service = notebook_service

    def run(self, data: NotebookEditInput, context: ToolExecutionContext) -> NotebookEditOutput:
        result = _notebook_service_for_context(self.notebook_service, context).edit_cell(data.path, data.index, data.source)
        return NotebookEditOutput(path=result["path"], index=result["index"], content=f"Edited notebook cell {data.index}")


def _notebook_service_for_context(service: NotebookService, context: ToolExecutionContext) -> NotebookService:
    return NotebookService(FileService(context.project_root)) if service.file_service.project_root != context.project_root else service

