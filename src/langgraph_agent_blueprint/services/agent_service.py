"""Service-layer helpers for subagent child-run boundaries."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from langgraph_agent_blueprint.graph.state import create_initial_state
from langgraph_agent_blueprint.models import ChildRunMetadata, SubagentRequest
from langgraph_agent_blueprint.utils.ids import new_id

if TYPE_CHECKING:
    from langgraph_agent_blueprint.tools.registry import ToolRegistry


class AgentService:
    """Prepare isolated child graph state for agent subgraphs."""

    max_depth = 1

    def create_child_metadata(self, parent_state: dict[str, Any], request: SubagentRequest) -> ChildRunMetadata:
        """Create validated parent/child identity metadata for one child run."""

        now = datetime.now(timezone.utc).isoformat()
        return ChildRunMetadata(
            child_run_id=new_id("child"),
            parent_session_id=str(parent_state.get("session_id") or "unknown"),
            parent_thread_id=str(parent_state.get("thread_id") or "unknown"),
            child_session_id=new_id("session"),
            child_thread_id=new_id("thread"),
            name=request.name,
            purpose=request.purpose,
            status="running",
            started_at=now,
            metadata={
                "parent_input_kind": parent_state.get("input_kind"),
                "requested_allowed_tools": list(request.allowed_tools),
            },
        )

    def create_child_state(
        self,
        parent_state: dict[str, Any],
        request: SubagentRequest,
        metadata: ChildRunMetadata,
        tool_registry: "ToolRegistry",
    ) -> dict[str, Any]:
        """Fork parent state into a serializable isolated child graph state."""

        parent_metadata = parent_state.get("metadata", {}) if isinstance(parent_state.get("metadata"), dict) else {}
        child_state = create_initial_state(
            request.prompt,
            project_root=parent_state.get("project_root"),
            project_id=parent_state.get("project_id"),
            workspace=copy.deepcopy(parent_state.get("workspace", {})),
            cwd=parent_state.get("cwd") or parent_state.get("project_root"),
            input_kind="headless",
            session_id=metadata.child_session_id,
            thread_id=metadata.child_thread_id,
        )
        allowed_tools = self.resolve_allowed_tools(parent_state, request, tool_registry)
        child_state["metadata"] = {
            "is_subagent": True,
            "subagent_depth": int(parent_metadata.get("subagent_depth", 0)) + 1,
            "child_run_id": metadata.child_run_id,
            "parent_session_id": metadata.parent_session_id,
            "parent_thread_id": metadata.parent_thread_id,
            "subagent_name": request.name,
            "subagent_purpose": request.purpose,
            "allowed_tools_override": allowed_tools if allowed_tools else ["__no_tools__"],
            "parent_context_summary": self._parent_context_summary(parent_state),
        }
        if request.inherit_memory:
            child_state["memory"] = copy.deepcopy(parent_state.get("memory", {}))
        if request.inherit_todos:
            child_state["todos"] = copy.deepcopy(parent_state.get("todos", []))
        if request.inherit_context:
            self._inherit_context(parent_state, child_state)
        return child_state

    def resolve_allowed_tools(
        self,
        parent_state: dict[str, Any],
        request: SubagentRequest,
        tool_registry: "ToolRegistry",
    ) -> list[str]:
        """Resolve a child tool scope without broadening an active parent scope."""

        available = tool_registry.all()
        parent_metadata = parent_state.get("metadata", {}) if isinstance(parent_state.get("metadata"), dict) else {}
        parent_scope = parent_metadata.get("allowed_tools_override")
        parent_scope_set = set(parent_scope) if isinstance(parent_scope, list) and parent_scope else None
        if request.allowed_tools:
            requested = list(dict.fromkeys(request.allowed_tools))
            unknown = [name for name in requested if name not in available]
            if unknown:
                raise ValueError(f"Unknown subagent allowed_tools: {', '.join(sorted(unknown))}")
            allowed = requested
        else:
            allowed = [
                name
                for name, tool in available.items()
                if tool.runtime.route == "execute" and tool.permission.is_read_only and not tool.permission.requires_permission
            ]
        if parent_scope_set is not None:
            allowed = [name for name in allowed if name in parent_scope_set]
        return allowed

    @staticmethod
    def _parent_context_summary(parent_state: dict[str, Any]) -> str:
        input_text = str(parent_state.get("input_text") or "")
        active_skill = parent_state.get("active_skill")
        skill_name = active_skill.get("name") if isinstance(active_skill, dict) else None
        parts = []
        if input_text:
            parts.append(f"Parent request: {input_text[:500]}")
        if skill_name:
            parts.append(f"Active skill: {skill_name}")
        return "\n".join(parts)

    @staticmethod
    def _inherit_context(parent_state: dict[str, Any], child_state: dict[str, Any]) -> None:
        """Copy already-resolved context metadata without sharing parent containers."""

        for key in ["context_references", "attachments", "resolved_context", "attachment_contents"]:
            child_state[key] = copy.deepcopy(parent_state.get(key, []))
        child_state["context_budget"] = copy.deepcopy(parent_state.get("context_budget", {}))
        parent_context = parent_state.get("context_status", {})
        if isinstance(parent_context, dict):
            child_context = dict(child_state.get("context_status", {}))
            for key in ["context_fragments", "context_provider_context", "context_budget", "context_errors"]:
                if key in parent_context:
                    child_context[key] = copy.deepcopy(parent_context.get(key))
            child_state["context_status"] = child_context
        metadata = dict(child_state.get("metadata", {}))
        metadata["context_inherited"] = True
        if child_state.get("resolved_context") or child_state.get("context_references"):
            metadata["context_resolved"] = True
        child_state["metadata"] = metadata
