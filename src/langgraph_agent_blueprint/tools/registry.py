"""ToolRegistry implementation and core tool registration factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph_agent_blueprint.services.agent_service import AgentService
from langgraph_agent_blueprint.services.diagnostics_service import DiagnosticsService
from langgraph_agent_blueprint.services.file_service import FileService
from langgraph_agent_blueprint.services.notebook_service import NotebookService
from langgraph_agent_blueprint.services.search_service import SearchService
from langgraph_agent_blueprint.services.shell_service import ShellService
from langgraph_agent_blueprint.services.web_service import WebService

from .agent_tools import AgentTool
from .base import BaseTool
from .diagnostics_tools import DiagnosticsTool
from .file_tools import FileEditTool, FileReadTool, FileWriteTool
from .notebook_tools import NotebookEditTool, NotebookReadTool
from .search_tools import GlobTool, GrepTool
from .shell_tools import BashTool, PowerShellTool
from .skill_tool import SkillTool
from .todo_tools import TodoWriteTool
from .web_tools import WebFetchTool, WebSearchTool


class ToolRegistry:
    """Central tool registry for built-in, MCP, plugin, and skill tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool[Any, Any]] = {}

    def register(self, tool: BaseTool[Any, Any]) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool[Any, Any]:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def all(self) -> dict[str, BaseTool[Any, Any]]:
        return dict(self._tools)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {name: tool.metadata() for name, tool in self._tools.items()}


def build_core_tool_registry(
    project_root: str | Path = ".",
    network_enabled: bool = False,
    web_fetch_allow_private_hosts: bool = False,
    web_fetch_max_bytes: int = 1_000_000,
    shell_timeout: float = 30.0,
    output_limit: int = 12000,
    skill_service: Any | None = None,
) -> ToolRegistry:
    """Instantiate core services and register the built-in model-callable tools."""

    root = Path(project_root).resolve()
    file_service = FileService(root)
    search_service = SearchService()
    shell_service = ShellService(root, timeout=shell_timeout, output_limit=output_limit)
    web_service = WebService(
        enabled=network_enabled,
        allow_private_hosts=web_fetch_allow_private_hosts,
        max_bytes=web_fetch_max_bytes,
    )
    notebook_service = NotebookService(file_service)
    registry = ToolRegistry()
    for tool in [
        FileReadTool(file_service),
        FileWriteTool(file_service),
        FileEditTool(file_service),
        NotebookReadTool(notebook_service),
        NotebookEditTool(notebook_service),
        GlobTool(search_service),
        GrepTool(search_service),
        BashTool(shell_service),
        PowerShellTool(shell_service),
        WebFetchTool(web_service),
        WebSearchTool(web_service),
        TodoWriteTool(),
        AgentTool(AgentService()),
        SkillTool(skill_service),
        DiagnosticsTool(DiagnosticsService()),
    ]:
        registry.register(tool)
    return registry

