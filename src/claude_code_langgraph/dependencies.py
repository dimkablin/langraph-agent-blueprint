from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from claude_code_langgraph.commands.registry import CommandRegistry, build_builtin_command_registry
from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.services.agent_service import AgentService
from claude_code_langgraph.services.command_service import CommandService
from claude_code_langgraph.services.compaction_service import CompactionService
from claude_code_langgraph.services.diagnostics_service import DiagnosticsService
from claude_code_langgraph.services.export_service import ExportService
from claude_code_langgraph.services.hook_service import HookService
from claude_code_langgraph.services.mcp_service import MCPService
from claude_code_langgraph.services.memory_service import MemoryService
from claude_code_langgraph.services.model_provider import ModelProviderService
from claude_code_langgraph.services.permission_service import PermissionService
from claude_code_langgraph.services.plugin_service import PluginService
from claude_code_langgraph.services.session_service import SessionService
from claude_code_langgraph.services.skill_service import SkillInvocationService
from claude_code_langgraph.services.task_service import TaskService
from claude_code_langgraph.services.tool_execution_service import ToolExecutionService
from claude_code_langgraph.services.usage_service import UsageService
from claude_code_langgraph.skills.registry import SkillRegistry, build_builtin_skill_registry
from claude_code_langgraph.storage.session_storage import SessionStorage
from claude_code_langgraph.tools.registry import ToolRegistry, build_core_tool_registry


@dataclass
class AppDependencies:
    """Dependency container injected into LangGraph node closures."""

    config: AppConfig
    model_provider: ModelProviderService
    command_registry: CommandRegistry
    skill_registry: SkillRegistry
    skill_service: SkillInvocationService
    tool_registry: ToolRegistry
    permission_service: PermissionService
    tool_execution_service: ToolExecutionService
    session_storage: SessionStorage
    session_service: SessionService
    memory_service: MemoryService
    compaction_service: CompactionService
    hook_service: HookService
    plugin_service: PluginService
    mcp_service: MCPService
    task_service: TaskService
    agent_service: AgentService
    export_service: ExportService
    diagnostics_service: DiagnosticsService
    command_service: CommandService
    usage_service: UsageService


def build_dependencies(config: AppConfig | None = None) -> AppDependencies:
    """Build all registries and services for a graph runtime."""

    config = config or AppConfig.from_env()
    project_root = Path(config.project_root or Path.cwd()).resolve()
    cwd = Path(config.cwd or project_root).resolve()
    config = config.model_copy(update={"project_root": project_root, "cwd": cwd, "storage_dir": Path(config.storage_dir).resolve()})
    skill_registry = build_builtin_skill_registry()
    if config.skills_paths:
        skill_registry.load_from_paths(config.skills_paths)
    skill_service = SkillInvocationService(skill_registry)
    tool_registry = build_core_tool_registry(
        project_root=project_root,
        network_enabled=config.network_enabled,
        shell_timeout=config.shell_timeout_seconds,
        output_limit=config.tool_output_limit,
        skill_service=skill_service,
    )
    mcp_service = MCPService(config.mcp_config)
    for definition in mcp_service.discover()["tools"].values():
        from claude_code_langgraph.tools.mcp_tools import MCPToolAdapter

        tool_registry.register(MCPToolAdapter(definition))
    command_registry = build_builtin_command_registry()
    session_storage = SessionStorage(config.storage_dir)
    return AppDependencies(
        config=config,
        model_provider=ModelProviderService(config),
        command_registry=command_registry,
        skill_registry=skill_registry,
        skill_service=skill_service,
        tool_registry=tool_registry,
        permission_service=PermissionService(config.permission_mode),
        tool_execution_service=ToolExecutionService(tool_registry, config.tool_output_limit),
        session_storage=session_storage,
        session_service=SessionService(session_storage),
        memory_service=MemoryService(config.storage_dir),
        compaction_service=CompactionService(
            max_messages_before_compact=max(3, config.auto_compact_threshold // 1000),
            keep_recent=config.max_recent_messages_after_compact,
        ),
        hook_service=HookService(),
        plugin_service=PluginService(config.plugin_paths),
        mcp_service=mcp_service,
        task_service=TaskService(),
        agent_service=AgentService(),
        export_service=ExportService(config.storage_dir),
        diagnostics_service=DiagnosticsService(),
        command_service=CommandService(command_registry),
        usage_service=UsageService(),
    )
