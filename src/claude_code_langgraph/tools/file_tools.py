from __future__ import annotations

from pydantic import BaseModel, Field

from claude_code_langgraph.services.file_service import FileService
from claude_code_langgraph.utils.truncation import truncate_text

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class FileReadInput(BaseModel):
    path: str
    offset: int | None = None
    limit: int | None = None


class FileReadOutput(ToolOutput):
    path: str


class FileReadTool(BaseTool[FileReadInput, FileReadOutput]):
    name = "read_file"
    description = "Read a text file under the project root, optionally with a line range."
    input_schema = FileReadInput
    output_schema = FileReadOutput
    safety = ToolSafety.READ_ONLY
    is_read_only = True
    requires_permission = False

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileReadInput, context: ToolExecutionContext) -> FileReadOutput:
        target = self.file_service.resolve(data.path)
        content = self.file_service.read_text(target, data.offset, data.limit)
        context.read_files.add(str(target))
        content, truncated = truncate_text(content, self.output_limit)
        return FileReadOutput(path=str(target), content=content, metadata={"truncated": truncated})


class FileWriteInput(BaseModel):
    path: str
    content: str = ""


class FileWriteOutput(ToolOutput):
    path: str
    diff: str = ""


class FileWriteTool(BaseTool[FileWriteInput, FileWriteOutput]):
    name = "write_file"
    description = "Create or overwrite a file under the project root."
    input_schema = FileWriteInput
    output_schema = FileWriteOutput
    safety = ToolSafety.WRITE
    is_read_only = False
    requires_permission = True

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileWriteInput, context: ToolExecutionContext) -> FileWriteOutput:
        result = self.file_service.write_text(data.path, data.content)
        return FileWriteOutput(path=result["path"], diff=result["diff"], content=f"Wrote {result['path']}")


class FileEditInput(BaseModel):
    path: str
    old_text: str
    new_text: str
    allow_unread: bool = False


class FileEditOutput(ToolOutput):
    path: str
    diff: str = ""


class FileEditTool(BaseTool[FileEditInput, FileEditOutput]):
    name = "edit_file"
    description = "Replace exact text in a file after it has been read or explicitly approved."
    input_schema = FileEditInput
    output_schema = FileEditOutput
    safety = ToolSafety.WRITE
    is_read_only = False
    requires_permission = True

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileEditInput, context: ToolExecutionContext) -> FileEditOutput:
        target = self.file_service.resolve(data.path)
        if str(target) not in context.read_files and not data.allow_unread:
            raise PermissionError("edit_file requires the file to be read first or explicit unread-edit approval")
        result = self.file_service.edit_text(target, data.old_text, data.new_text)
        return FileEditOutput(path=result["path"], diff=result["diff"], content=f"Edited {result['path']}")

