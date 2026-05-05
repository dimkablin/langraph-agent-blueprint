from __future__ import annotations

from fastapi import FastAPI

from claude_code_langgraph.config import AppConfig
from claude_code_langgraph.dependencies import build_dependencies
from claude_code_langgraph.graph.builder import AssistantGraphRuntime

from .schemas import ApprovalRequest, ChatRequest, ChatResponse
from .routes_chat import router as chat_router
from .routes_commands import router as commands_router
from .routes_mcp import router as mcp_router
from .routes_sessions import router as sessions_router
from .routes_skills import router as skills_router
from .routes_tools import router as tools_router


def create_app(config: AppConfig | None = None) -> FastAPI:
    api = FastAPI(title="claude-code-langgraph")
    runtime = AssistantGraphRuntime(build_dependencies(config or AppConfig.from_env()))
    api.state.runtime = runtime

    @api.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        result = runtime.invoke(request.message, input_kind="headless", session_id=request.session_id, thread_id=request.thread_id)
        permission_required = None
        if "__interrupt__" in result:
            permission_required = result["__interrupt__"][0].value
        return ChatResponse(
            session_id=result["session_id"],
            thread_id=result["thread_id"],
            final_response=result.get("final_response"),
            events=result.get("ui_events", []),
            permission_required=permission_required,
        )

    @api.post("/approval", response_model=ChatResponse)
    def approval(request: ApprovalRequest) -> ChatResponse:
        result = runtime.resume(request.thread_id, request.decision)
        return ChatResponse(
            session_id=result["session_id"],
            thread_id=result["thread_id"],
            final_response=result.get("final_response"),
            events=result.get("ui_events", []),
            permission_required=None,
        )

    @api.get("/skills")
    def skills() -> dict:
        return runtime.dependencies.skill_registry.snapshot()

    @api.get("/tools")
    def tools() -> dict:
        return runtime.dependencies.tool_registry.snapshot()

    @api.get("/commands")
    def commands() -> dict:
        return runtime.dependencies.command_registry.snapshot()

    api.include_router(sessions_router)
    api.include_router(chat_router)
    api.include_router(skills_router)
    api.include_router(tools_router)
    api.include_router(commands_router)
    api.include_router(mcp_router)
    return api
