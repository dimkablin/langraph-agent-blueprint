"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel, Field

from claude_code_langgraph.models.tool_metadata import ToolPermissionMetadata, ToolRuntimeMetadata
from claude_code_langgraph.services.file_service import FileService
from claude_code_langgraph.utils.truncation import truncate_text

from .base import BaseTool, ToolExecutionContext, ToolOutput


class FileReadInput(BaseModel):
    """Pydantic input schema for the file read operation."""
    path: str
    offset: int | None = None
    limit: int | None = None


class FileReadOutput(ToolOutput):
    """Pydantic output schema for the file read operation."""
    path: str


class FileReadTool(BaseTool[FileReadInput, FileReadOutput]):
    """Model-callable tool that reads text files under the configured project root."""
    name = "read_file"
    description = "Read a text file under the project root, optionally with a line range."
    input_schema = FileReadInput
    output_schema = FileReadOutput
    permission = ToolPermissionMetadata(action="read", risk="low", is_read_only=True, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="file", state_effects=["record_file_read"])

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileReadInput, context: ToolExecutionContext) -> FileReadOutput:
        target = self.file_service.resolve(data.path)
        content = self.file_service.read_text(target, data.offset, data.limit)
        context.read_files.add(str(target))
        content, truncated = truncate_text(content, self.output_limit)
        return FileReadOutput(path=str(target), content=content, metadata={"truncated": truncated})


class FileWriteInput(BaseModel):
    """Pydantic input schema for the file write operation."""
    path: str
    content: str = ""


class FileWriteOutput(ToolOutput):
    """Pydantic output schema for the file write operation."""
    path: str
    diff: str = ""


class FileWriteTool(BaseTool[FileWriteInput, FileWriteOutput]):
    """Model-callable tool that creates or overwrites project files after permission approval."""
    name = "write_file"
    description = "Create or overwrite a file under the project root."
    input_schema = FileWriteInput
    output_schema = FileWriteOutput
    permission = ToolPermissionMetadata(action="write", risk="medium", requires_permission=True, reason="This tool modifies files.")
    runtime = ToolRuntimeMetadata(kind="file", state_effects=["record_file_write"])

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileWriteInput, context: ToolExecutionContext) -> FileWriteOutput:
        result = self.file_service.write_text(data.path, data.content)
        return FileWriteOutput(path=result["path"], diff=result["diff"], content=f"Wrote {result['path']}")


class FileEditInput(BaseModel):
    """Pydantic input schema for the file edit operation."""
    path: str
    old_text: str
    new_text: str
    allow_unread: bool = False


class FileEditOutput(ToolOutput):
    """Pydantic output schema for the file edit operation."""
    path: str
    diff: str = ""


class FileEditTool(BaseTool[FileEditInput, FileEditOutput]):
    """Model-callable tool that applies exact-text edits with prior-read and permission safeguards."""
    name = "edit_file"
    description = "Replace exact text in a file after it has been read or explicitly approved."
    input_schema = FileEditInput
    output_schema = FileEditOutput
    permission = ToolPermissionMetadata(action="edit", risk="medium", requires_permission=True, reason="This tool edits files.")
    runtime = ToolRuntimeMetadata(kind="file", state_effects=["record_file_edit"])

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileEditInput, context: ToolExecutionContext) -> FileEditOutput:
        target = self.file_service.resolve(data.path)
        if str(target) not in context.read_files and not data.allow_unread:
            raise PermissionError("edit_file requires the file to be read first or explicit unread-edit approval")
        result = self.file_service.edit_text(target, data.old_text, data.new_text)
        return FileEditOutput(path=result["path"], diff=result["diff"], content=f"Edited {result['path']}")

