"""Dependency container factory that wires registries, services, storage, providers, and graph nodes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langgraph_agent_blueprint.commands.registry import CommandRegistry, build_builtin_command_registry
from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.hooks.registry import HookRegistry
from langgraph_agent_blueprint.services.agent_service import AgentService
from langgraph_agent_blueprint.services.command_service import CommandService
from langgraph_agent_blueprint.services.compaction_service import CompactionService
from langgraph_agent_blueprint.services.diagnostics_service import DiagnosticsService
from langgraph_agent_blueprint.services.export_service import ExportService
from langgraph_agent_blueprint.services.hook_service import HookService
from langgraph_agent_blueprint.services.mcp_service import MCPService
from langgraph_agent_blueprint.services.memory_service import MemoryService
from langgraph_agent_blueprint.services.model_provider import ModelProviderService
from langgraph_agent_blueprint.services.permission_service import PermissionService
from langgraph_agent_blueprint.services.plugin_service import PluginService
from langgraph_agent_blueprint.services.session_service import SessionService
from langgraph_agent_blueprint.services.skill_service import SkillInvocationService
from langgraph_agent_blueprint.services.task_service import TaskService
from langgraph_agent_blueprint.services.tool_execution_service import ToolExecutionService
from langgraph_agent_blueprint.services.usage_service import UsageService
from langgraph_agent_blueprint.skills.registry import SkillRegistry, build_builtin_skill_registry
from langgraph_agent_blueprint.storage.session_storage import SessionStorage
from langgraph_agent_blueprint.tools.registry import ToolRegistry, build_core_tool_registry


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
    hook_registry: HookRegistry
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
    plugin_service = PluginService(config.plugin_paths, config.storage_dir, network_enabled=config.network_enabled)
    plugin_contributions = plugin_service.discover_contributions()
    skill_registry = build_builtin_skill_registry()
    skill_registry.load_plugin_contributions(plugin_contributions)
    hook_registry = HookRegistry()
    for contribution in plugin_contributions:
        for hook in contribution.hooks:
            hook_registry.register(hook)
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
    mcp_service = MCPService(config.mcp_config, output_limit=config.tool_output_limit)
    for definition in mcp_service.discover()["tools"].values():
        from langgraph_agent_blueprint.tools.mcp_tools import MCPToolAdapter

        tool_registry.register(MCPToolAdapter(definition, mcp_service))
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
        hook_registry=hook_registry,
        hook_service=HookService(hook_registry),
        plugin_service=plugin_service,
        mcp_service=mcp_service,
        task_service=TaskService(),
        agent_service=AgentService(),
        export_service=ExportService(config.storage_dir),
        diagnostics_service=DiagnosticsService(),
        command_service=CommandService(command_registry),
        usage_service=UsageService(),
    )
