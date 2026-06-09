"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel, Field

from langgraph_agent_blueprint.models import ToolActivitySpec, ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services import SearchService
from langgraph_agent_blueprint.utils.path_contract import PROJECT_RELATIVE_DIRECTORY_DESCRIPTION
from langgraph_agent_blueprint.utils.paths import resolve_under_root

from .base import BaseTool, ToolExecutionContext, ToolOutput


class GlobInput(BaseModel):
    """Pydantic input schema for the glob operation."""
    pattern: str = Field(description="Glob pattern to match under the workspace root or optional path.")
    path: str | None = Field(default=None, description=PROJECT_RELATIVE_DIRECTORY_DESCRIPTION)


class GlobOutput(ToolOutput):
    """Pydantic output schema for the glob operation."""
    matches: list[str]


class GlobTool(BaseTool[GlobInput, GlobOutput]):
    """Model-callable tool that finds files by glob pattern inside the project root."""
    name = "glob"
    description = "Find files by glob pattern under the project root."
    input_schema = GlobInput
    output_schema = GlobOutput
    permission = ToolPermissionMetadata(action="read", risk="low", is_read_only=True, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="search")
    activity = ToolActivitySpec(
        display_name="Find files",
        started_type="tool.glob.started",
        completed_type="tool.glob.completed",
        failed_type="tool.glob.failed",
    )

    def __init__(self, search_service: SearchService) -> None:
        self.search_service = search_service

    def run(self, data: GlobInput, context: ToolExecutionContext) -> GlobOutput:
        root = resolve_under_root(data.path, context.project_root) if data.path else context.project_root
        matches = self.search_service.glob(root, data.pattern)
        return GlobOutput(matches=matches, content="\n".join(matches))

    def activity_started_data(self, data: GlobInput | None, context: ToolExecutionContext) -> dict[str, object]:
        return {"operation": "search.glob", "pattern": data.pattern if data else "", "path": data.path if data else None}

    def activity_completed_data(self, data: GlobInput, output: GlobOutput, context: ToolExecutionContext) -> dict[str, object]:
        return {"operation": "search.glob", "pattern": data.pattern, "path": data.path, "result_count": len(output.matches)}

    def activity_started_summary(self, data: GlobInput | None, context: ToolExecutionContext) -> str | None:
        return f"Finding files matching `{data.pattern}`." if data else "Finding files."

    def activity_completed_summary(self, data: GlobInput, output: GlobOutput, context: ToolExecutionContext) -> str | None:
        return f"Found {len(output.matches)} file match(es)."


class GrepInput(BaseModel):
    """Pydantic input schema for the grep operation."""
    pattern: str = Field(description="Text or regular expression pattern to search for.")
    path: str | None = Field(default=None, description=PROJECT_RELATIVE_DIRECTORY_DESCRIPTION)
    include: str | None = Field(default=None, description="Optional glob pattern for files to include.")
    exclude: str | None = Field(default=None, description="Optional glob pattern for files to exclude.")
    max_results: int = Field(default=100, description="Maximum number of matches to return.")


class GrepOutput(ToolOutput):
    """Pydantic output schema for the grep operation."""
    matches: list[dict[str, object]]


class GrepTool(BaseTool[GrepInput, GrepOutput]):
    """Model-callable tool that searches file contents with ripgrep or Python fallback."""
    name = "grep"
    description = "Search file contents under the project root."
    input_schema = GrepInput
    output_schema = GrepOutput
    permission = ToolPermissionMetadata(action="read", risk="low", is_read_only=True, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="search")
    activity = ToolActivitySpec(
        display_name="Search text",
        started_type="tool.grep.started",
        completed_type="tool.grep.completed",
        failed_type="tool.grep.failed",
    )

    def __init__(self, search_service: SearchService) -> None:
        self.search_service = search_service

    def run(self, data: GrepInput, context: ToolExecutionContext) -> GrepOutput:
        root = resolve_under_root(data.path, context.project_root) if data.path else context.project_root
        matches = self.search_service.grep(root, data.pattern, data.include, data.exclude, data.max_results)
        content = "\n".join(f"{m['path']}:{m['line']}: {m['text']}" for m in matches)
        return GrepOutput(matches=matches, content=content)

    def activity_started_data(self, data: GrepInput | None, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "search.grep",
            "pattern": data.pattern if data else "",
            "path": data.path if data else None,
            "include": data.include if data else None,
            "exclude": data.exclude if data else None,
            "max_results": data.max_results if data else None,
        }

    def activity_completed_data(self, data: GrepInput, output: GrepOutput, context: ToolExecutionContext) -> dict[str, object]:
        return {
            "operation": "search.grep",
            "pattern": data.pattern,
            "path": data.path,
            "include": data.include,
            "exclude": data.exclude,
            "max_results": data.max_results,
            "result_count": len(output.matches),
        }

    def activity_started_summary(self, data: GrepInput | None, context: ToolExecutionContext) -> str | None:
        return f"Searching for `{data.pattern}`." if data else "Searching text."

    def activity_completed_summary(self, data: GrepInput, output: GrepOutput, context: ToolExecutionContext) -> str | None:
        return f"Found {len(output.matches)} text match(es)."

