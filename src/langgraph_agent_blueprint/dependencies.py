"""Dependency container factory that wires registries, services, storage, providers, and graph nodes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langgraph_agent_blueprint.commands import CommandRegistry, build_builtin_command_registry
from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.context import ContextBudgetService, ContextProviderService
from langgraph_agent_blueprint.hooks import HookRegistry
from langgraph_agent_blueprint.services import (
    AgentService,
    CommandService,
    CompactionService,
    ConversationService,
    DiagnosticsService,
    ExportService,
    FolderPickerService,
    HookService,
    MCPService,
    MemoryService,
    ModelProviderService,
    ObservabilityService,
    PermissionService,
    PluginService,
    RunControlService,
    RunEventStreamService,
    SessionService,
    SkillInvocationService,
    TaskService,
    UsageService,
    WebService,
    WorkspaceService,
)
from langgraph_agent_blueprint.services.tool_execution_service import ToolExecutionService
from langgraph_agent_blueprint.skills import SkillRegistry, build_builtin_skill_registry
from langgraph_agent_blueprint.storage import SQLiteConversationStorage, SessionStorage
from langgraph_agent_blueprint.tools import PluginToolAdapter, ToolRegistry, build_core_tool_registry


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
    conversation_service: ConversationService
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
    observability_service: ObservabilityService
    run_control_service: RunControlService
    run_event_stream_service: RunEventStreamService
    context_provider_service: ContextProviderService
    context_budget_service: ContextBudgetService
    workspace_service: WorkspaceService
    folder_picker_service: FolderPickerService


def build_dependencies(config: AppConfig | None = None) -> AppDependencies:
    """Build all registries and services for a graph runtime."""

    config = config or AppConfig.from_env()
    project_root = Path(config.project_root or Path.cwd()).resolve()
    cwd = Path(config.cwd or project_root).resolve()
    config = config.model_copy(update={"project_root": project_root, "cwd": cwd, "storage_dir": Path(config.storage_dir).resolve()})
    plugin_service = PluginService(
        config.plugin_paths,
        config.storage_dir,
        network_enabled=config.network_enabled,
        git_timeout_seconds=config.plugin_git_timeout_seconds,
    )
    plugin_contributions = plugin_service.discover_contributions()
    mcp_config = _merge_plugin_mcp_config(config.mcp_config, plugin_contributions)
    config = config.model_copy(update={"mcp_config": mcp_config})
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
        web_fetch_allow_private_hosts=config.web_fetch_allow_private_hosts,
        web_fetch_max_bytes=config.web_fetch_max_bytes,
        shell_timeout=config.shell_timeout_seconds,
        output_limit=config.tool_output_limit,
        skill_service=skill_service,
    )
    for contribution in plugin_contributions:
        if not contribution.enabled:
            continue
        for tool in contribution.tools:
            if tool.enabled:
                tool_registry.register(PluginToolAdapter(tool))
    mcp_service = MCPService(config.mcp_config, output_limit=config.tool_output_limit)
    context_web_service = WebService(
        enabled=config.network_enabled,
        allow_private_hosts=config.web_fetch_allow_private_hosts,
        max_bytes=config.web_fetch_max_bytes,
    )
    context_provider_service = ContextProviderService(
        project_root=project_root,
        mcp_service=mcp_service,
        web_service=context_web_service,
        max_file_bytes=config.context_max_file_bytes,
        max_directory_files=config.context_max_directory_files,
        max_glob_files=config.context_max_glob_files,
        plugin_context_providers=[
            provider
            for contribution in plugin_contributions
            if contribution.enabled
            for provider in contribution.context_providers
            if provider.enabled
        ],
    )
    command_registry = build_builtin_command_registry()
    command_registry.register_plugin_contributions(plugin_contributions)
    session_storage = SessionStorage(config.storage_dir)
    conversation_storage = SQLiteConversationStorage(config.storage_dir / "conversations.sqlite3")
    workspace_service = WorkspaceService(config.storage_dir)
    folder_picker_service = FolderPickerService()
    return AppDependencies(
        config=config,
        model_provider=ModelProviderService(config),
        command_registry=command_registry,
        skill_registry=skill_registry,
        skill_service=skill_service,
        tool_registry=tool_registry,
        permission_service=PermissionService(config.permission_mode),
        tool_execution_service=ToolExecutionService(tool_registry, config.tool_output_limit, session_storage),
        session_storage=session_storage,
        session_service=SessionService(session_storage),
        conversation_service=ConversationService(conversation_storage),
        memory_service=MemoryService(config.storage_dir),
        compaction_service=CompactionService(
            max_tokens_before_compact=config.auto_compact_threshold,
            keep_recent=config.max_recent_messages_after_compact,
            context_window_max_tokens=config.context_max_tokens,
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
        observability_service=ObservabilityService(config.langfuse),
        run_control_service=RunControlService(),
        run_event_stream_service=RunEventStreamService(),
        context_provider_service=context_provider_service,
        context_budget_service=ContextBudgetService(config.context_max_tokens),
        workspace_service=workspace_service,
        folder_picker_service=folder_picker_service,
    )


def _merge_plugin_mcp_config(base: dict, plugin_contributions: list) -> dict:
    merged = dict(base or {})
    servers = dict(merged.get("servers") or {})
    for contribution in plugin_contributions:
        if not contribution.enabled:
            continue
        for server in contribution.mcp_servers:
            if not server.enabled:
                continue
            servers[server.registry_name] = dict(server.config)
    if servers:
        merged["servers"] = servers
    return merged
