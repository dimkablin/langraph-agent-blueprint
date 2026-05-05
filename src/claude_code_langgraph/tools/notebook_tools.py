from __future__ import annotations

from pydantic import BaseModel

from claude_code_langgraph.services.notebook_service import NotebookService

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class NotebookReadInput(BaseModel):
    path: str


class NotebookReadOutput(ToolOutput):
    cells: list[dict[str, object]]


class NotebookReadTool(BaseTool[NotebookReadInput, NotebookReadOutput]):
    name = "notebook_read"
    description = "Read Jupyter notebook cells and metadata."
    input_schema = NotebookReadInput
    output_schema = NotebookReadOutput
    safety = ToolSafety.READ_ONLY
    is_read_only = True
    requires_permission = False

    def __init__(self, notebook_service: NotebookService) -> None:
        self.notebook_service = notebook_service

    def run(self, data: NotebookReadInput, context: ToolExecutionContext) -> NotebookReadOutput:
        result = self.notebook_service.read(data.path)
        return NotebookReadOutput(content=f"Read notebook {result['path']}", cells=result["cells"], metadata=result)


class NotebookEditInput(BaseModel):
    path: str
    index: int
    source: str


class NotebookEditOutput(ToolOutput):
    path: str
    index: int


class NotebookEditTool(BaseTool[NotebookEditInput, NotebookEditOutput]):
    name = "notebook_edit"
    description = "Edit a Jupyter notebook cell."
    input_schema = NotebookEditInput
    output_schema = NotebookEditOutput
    safety = ToolSafety.WRITE
    is_read_only = False
    requires_permission = True

    def __init__(self, notebook_service: NotebookService) -> None:
        self.notebook_service = notebook_service

    def run(self, data: NotebookEditInput, context: ToolExecutionContext) -> NotebookEditOutput:
        result = self.notebook_service.edit_cell(data.path, data.index, data.source)
        return NotebookEditOutput(path=result["path"], index=result["index"], content=f"Edited notebook cell {data.index}")

