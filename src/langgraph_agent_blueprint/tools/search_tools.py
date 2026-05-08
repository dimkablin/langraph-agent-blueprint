"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel

from langgraph_agent_blueprint.models import ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services import SearchService
from langgraph_agent_blueprint.utils.paths import resolve_under_root

from .base import BaseTool, ToolExecutionContext, ToolOutput


class GlobInput(BaseModel):
    """Pydantic input schema for the glob operation."""
    pattern: str
    path: str | None = None


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

    def __init__(self, search_service: SearchService) -> None:
        self.search_service = search_service

    def run(self, data: GlobInput, context: ToolExecutionContext) -> GlobOutput:
        root = resolve_under_root(data.path, context.project_root) if data.path else context.project_root
        matches = self.search_service.glob(root, data.pattern)
        return GlobOutput(matches=matches, content="\n".join(matches))


class GrepInput(BaseModel):
    """Pydantic input schema for the grep operation."""
    pattern: str
    path: str | None = None
    include: str | None = None
    exclude: str | None = None
    max_results: int = 100


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

    def __init__(self, search_service: SearchService) -> None:
        self.search_service = search_service

    def run(self, data: GrepInput, context: ToolExecutionContext) -> GrepOutput:
        root = resolve_under_root(data.path, context.project_root) if data.path else context.project_root
        matches = self.search_service.grep(root, data.pattern, data.include, data.exclude, data.max_results)
        content = "\n".join(f"{m['path']}:{m['line']}: {m['text']}" for m in matches)
        return GrepOutput(matches=matches, content=content)

