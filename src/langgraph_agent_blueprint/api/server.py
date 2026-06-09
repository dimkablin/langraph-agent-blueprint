"""FastAPI application factory that mounts graph-facing routes and shared runtime state."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from langgraph_agent_blueprint.config import AppConfig
from langgraph_agent_blueprint.dependencies import build_dependencies
from langgraph_agent_blueprint.graph.builder import AssistantGraphRuntime
from langgraph_agent_blueprint.models.conversations import ConversationCreate, MessageCreate
from langgraph_agent_blueprint.services.conversation_service import ConversationAccessError, event_creates_from_runtime, title_from_message
from langgraph_agent_blueprint.services.workspace_service import WorkspaceNotFoundError, WorkspacePathError

from .routes_chat import router as chat_router
from .routes_commands import router as commands_router
from .routes_conversations import router as conversations_router
from .routes_mcp import router as mcp_router
from .routes_sessions import router as sessions_router
from .routes_skills import router as skills_router
from .routes_status import router as status_router
from .routes_tools import router as tools_router
from .routes_workspaces import router as workspaces_router
from .schemas import ApprovalRequest, ChatRequest, ChatResponse
from .serializers import runtime_event_dtos


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Create the FastAPI adapter and attach a shared graph runtime to application state.

    Route handlers delegate chat, approval, registry, and session operations to the same
    AssistantGraphRuntime used by CLI/headless modes.
    """

    config = config or AppConfig.from_env()
    api = FastAPI(title="langgraph-agent-blueprint")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-User-Id"],
    )
    runtime = AssistantGraphRuntime(build_dependencies(config))
    api.state.runtime = runtime

    @api.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest, x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> ChatResponse:
        runtime = api.state.runtime
        conversation_service = getattr(runtime.dependencies, "conversation_service", None)
        user_id = _user_id(x_user_id)
        conversation = None
        if conversation_service is not None:
            if request.session_id:
                try:
                    conversation = conversation_service.get_conversation(user_id, request.session_id).conversation
                except ConversationAccessError as exc:
                    raise HTTPException(status_code=404, detail=str(exc)) from exc
            else:
                conversation = conversation_service.create_conversation(
                    user_id,
                    ConversationCreate(title=title_from_message(request.message), project_id=request.project_id),
                )
        session_id = conversation.session_id if conversation is not None else request.session_id
        thread_id = conversation.thread_id if conversation is not None else request.thread_id
        attachments = [item.model_dump(mode="json", exclude_none=True) for item in request.attachments]
        try:
            result = runtime.invoke(
                request.message,
                input_kind="headless",
                project_id=request.project_id,
                session_id=session_id,
                thread_id=thread_id,
                model_intelligence=request.model_intelligence,
                permission_mode=request.permission_mode,
                attachments=attachments,
            )
        except WorkspaceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WorkspacePathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        permission_required = None
        if "__interrupt__" in result:
            permission_required = result["__interrupt__"][0].value
        final_response = result.get("final_response")
        if conversation_service is not None and conversation is not None and (final_response is not None or result.get("ui_events")):
            conversation_service.append_turn(
                user_id,
                conversation.conversation_id,
                user_message=MessageCreate(role="user", content=request.message),
                assistant_message=MessageCreate(role="assistant", content=str(final_response or "")) if final_response is not None else None,
                events=event_creates_from_runtime(result.get("ui_events", [])),
            )
        return ChatResponse(
            session_id=result["session_id"],
            thread_id=result["thread_id"],
            conversation_id=conversation.conversation_id if conversation is not None else result.get("session_id"),
            final_response=result.get("final_response"),
            events=runtime_event_dtos(
                result.get("ui_events", []),
                redactor=runtime.dependencies.observability_service.redact_payload,
            ),
            usage=result.get("usage", {}) or {},
            permission_required=permission_required,
        )

    @api.post("/approval", response_model=ChatResponse)
    def approval(request: ApprovalRequest, x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> ChatResponse:
        runtime = api.state.runtime
        conversation_service = getattr(runtime.dependencies, "conversation_service", None)
        user_id = _required_user_id(x_user_id)
        conversation = None
        if conversation_service is not None:
            try:
                conversation = conversation_service.get_conversation_for_thread(
                    user_id,
                    session_id=request.session_id,
                    thread_id=request.thread_id,
                ).conversation
            except ConversationAccessError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        result = runtime.resume(request.thread_id, request.decision_payload(), session_id=request.session_id)
        permission_required = None
        if "__interrupt__" in result:
            permission_required = result["__interrupt__"][0].value
        if conversation_service is not None and conversation is not None and (result.get("final_response") is not None or result.get("ui_events")):
            final_response = result.get("final_response")
            conversation_service.append_turn(
                user_id,
                conversation.conversation_id,
                assistant_message=MessageCreate(role="assistant", content=str(final_response or "")) if final_response is not None else None,
                events=event_creates_from_runtime(result.get("ui_events", [])),
            )
        return ChatResponse(
            session_id=result["session_id"],
            thread_id=result["thread_id"],
            conversation_id=conversation.conversation_id if conversation is not None else result.get("session_id"),
            final_response=result.get("final_response"),
            events=runtime_event_dtos(
                result.get("ui_events", []),
                redactor=runtime.dependencies.observability_service.redact_payload,
            ),
            usage=result.get("usage", {}) or {},
            permission_required=permission_required,
        )

    api.include_router(sessions_router)
    api.include_router(conversations_router)
    api.include_router(chat_router)
    api.include_router(skills_router)
    api.include_router(tools_router)
    api.include_router(commands_router)
    api.include_router(mcp_router)
    api.include_router(status_router)
    api.include_router(workspaces_router)
    return api


def _required_user_id(header_value: str | None) -> str:
    if header_value is None:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return _user_id(header_value)


def _user_id(header_value: str | None) -> str:
    user_id = (header_value or "dev-user").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header cannot be empty")
    if len(user_id) > 128:
        raise HTTPException(status_code=400, detail="X-User-Id header is too long")
    return user_id
