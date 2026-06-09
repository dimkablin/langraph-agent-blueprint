"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models import AgentActivityRef, ToolActivitySpec, ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services import FileService
from langgraph_agent_blueprint.utils.activity import safe_display_path
from langgraph_agent_blueprint.utils.path_contract import PROJECT_RELATIVE_PATH_DESCRIPTION
from langgraph_agent_blueprint.utils.truncation import truncate_text

from .base import BaseTool, ToolExecutionContext, ToolOutput


class FileReadInput(BaseModel):
    """Pydantic input schema for the file read operation."""
    path: str = Field(description=PROJECT_RELATIVE_PATH_DESCRIPTION)
    offset: int | None = Field(default=None, description="Optional zero-based line offset to start reading from.")
    limit: int | None = Field(default=None, description="Optional maximum number of lines to read.")


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
    activity = ToolActivitySpec(
        display_name="Read file",
        started_type="tool.read_file.started",
        completed_type="tool.read_file.completed",
        failed_type="tool.read_file.failed",
        blocked_type="tool.read_file.blocked",
    )

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileReadInput, context: ToolExecutionContext) -> FileReadOutput:
        file_service = self.file_service.for_root(context.project_root)
        target = file_service.resolve(data.path)
        content = file_service.read_text(target, data.offset, data.limit)
        content, truncated = truncate_text(content, self.output_limit)
        return FileReadOutput(path=str(target), content=content, metadata={"truncated": truncated})

    def activity_started_data(self, data: FileReadInput | None, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "file.read",
            "path": data.path if data else None,
            "offset": data.offset if data else None,
            "limit": data.limit if data else None,
        }

    def activity_completed_data(self, data: FileReadInput, output: FileReadOutput, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "file.read",
            "path": safe_display_path(output.path, context.project_root),
            "content_chars": len(output.content),
            "truncated": bool(output.metadata.get("truncated")),
        }

    def activity_started_summary(self, data: FileReadInput | None, context: ToolExecutionContext) -> str | None:
        return f"Reading {data.path}." if data else "Reading file."

    def activity_completed_summary(self, data: FileReadInput, output: FileReadOutput, context: ToolExecutionContext) -> str | None:
        path = safe_display_path(output.path, context.project_root)
        return f"Read {path}."

    def activity_refs(
        self,
        *,
        data: FileReadInput | None,
        output: FileReadOutput | None,
        context: ToolExecutionContext,
    ) -> list[AgentActivityRef]:
        path = safe_display_path(output.path if output else getattr(data, "path", None), context.project_root)
        return [AgentActivityRef(kind="file", path=path)] if path else []


class FileWriteInput(BaseModel):
    """Pydantic input schema for the file write operation."""
    path: str = Field(description=PROJECT_RELATIVE_PATH_DESCRIPTION)
    content: str = Field(default="", description="Complete file content to write.")


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
    activity = ToolActivitySpec(
        display_name="Write file",
        started_type="tool.write_file.started",
        completed_type="tool.write_file.completed",
        failed_type="tool.write_file.failed",
        blocked_type="tool.write_file.blocked",
    )

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileWriteInput, context: ToolExecutionContext) -> FileWriteOutput:
        result = self.file_service.for_root(context.project_root).write_text(data.path, data.content)
        return FileWriteOutput(path=result["path"], diff=result["diff"], content=f"Wrote {result['path']}")

    def activity_started_data(self, data: FileWriteInput | None, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "file.write",
            "path": data.path if data else None,
            "content_chars": len(data.content) if data else 0,
        }

    def activity_completed_data(self, data: FileWriteInput, output: FileWriteOutput, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "file.write",
            "path": safe_display_path(output.path, context.project_root),
            "content_chars": len(data.content),
            "diff_lines": len(output.diff.splitlines()),
        }

    def activity_started_summary(self, data: FileWriteInput | None, context: ToolExecutionContext) -> str | None:
        return f"Writing {data.path}." if data else "Writing file."

    def activity_completed_summary(self, data: FileWriteInput, output: FileWriteOutput, context: ToolExecutionContext) -> str | None:
        return f"Wrote {safe_display_path(output.path, context.project_root)}."

    def activity_refs(
        self,
        *,
        data: FileWriteInput | None,
        output: FileWriteOutput | None,
        context: ToolExecutionContext,
    ) -> list[AgentActivityRef]:
        path = safe_display_path(output.path if output else getattr(data, "path", None), context.project_root)
        return [AgentActivityRef(kind="file", path=path)] if path else []


class FileEditInput(BaseModel):
    """Pydantic input schema for the file edit operation."""
    path: str = Field(description=PROJECT_RELATIVE_PATH_DESCRIPTION)
    old_text: str = Field(description="Exact text currently present in the file.")
    new_text: str = Field(description="Replacement text to write in place of old_text.")
    allow_unread: bool = Field(default=False, description="Allow editing a file that has not been read in this run.")


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
    activity = ToolActivitySpec(
        display_name="Edit file",
        started_type="tool.edit_file.started",
        completed_type="tool.edit_file.completed",
        failed_type="tool.edit_file.failed",
        blocked_type="tool.edit_file.blocked",
    )

    def __init__(self, file_service: FileService) -> None:
        self.file_service = file_service

    def run(self, data: FileEditInput, context: ToolExecutionContext) -> FileEditOutput:
        file_service = self.file_service.for_root(context.project_root)
        target = file_service.resolve(data.path)
        if str(target) not in context.read_files and not data.allow_unread:
            raise PermissionError("edit_file requires the file to be read first or explicit unread-edit approval")
        result = file_service.edit_text(target, data.old_text, data.new_text)
        return FileEditOutput(path=result["path"], diff=result["diff"], content=f"Edited {result['path']}")

    def activity_started_data(self, data: FileEditInput | None, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "file.edit",
            "path": data.path if data else None,
            "old_text_chars": len(data.old_text) if data else 0,
            "new_text_chars": len(data.new_text) if data else 0,
            "allow_unread": bool(data.allow_unread) if data else False,
        }

    def activity_completed_data(self, data: FileEditInput, output: FileEditOutput, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "file.edit",
            "path": safe_display_path(output.path, context.project_root),
            "old_text_chars": len(data.old_text),
            "new_text_chars": len(data.new_text),
            "diff_lines": len(output.diff.splitlines()),
        }

    def activity_started_summary(self, data: FileEditInput | None, context: ToolExecutionContext) -> str | None:
        return f"Editing {data.path}." if data else "Editing file."

    def activity_completed_summary(self, data: FileEditInput, output: FileEditOutput, context: ToolExecutionContext) -> str | None:
        return f"Edited {safe_display_path(output.path, context.project_root)}."

    def activity_refs(
        self,
        *,
        data: FileEditInput | None,
        output: FileEditOutput | None,
        context: ToolExecutionContext,
    ) -> list[AgentActivityRef]:
        path = safe_display_path(output.path if output else getattr(data, "path", None), context.project_root)
        return [AgentActivityRef(kind="file", path=path)] if path else []

