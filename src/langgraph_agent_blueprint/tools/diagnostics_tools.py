"""Model-callable tool module exposing typed operations through the central ToolRegistry."""

from __future__ import annotations

from pydantic import BaseModel

from langgraph_agent_blueprint.models import ToolPermissionMetadata, ToolRuntimeMetadata
from langgraph_agent_blueprint.services import DiagnosticsService

from .base import BaseTool, ToolExecutionContext, ToolOutput


class DiagnosticsInput(BaseModel):
    """Pydantic input schema for the diagnostics operation."""
    verbose: bool = False


class DiagnosticsOutput(ToolOutput):
    """Pydantic output schema for the diagnostics operation."""
    diagnostics: dict[str, object]


class DiagnosticsTool(BaseTool[DiagnosticsInput, DiagnosticsOutput]):
    """Model-callable tool that reports runtime and environment diagnostics."""
    name = "diagnostics"
    description = "Run project and environment diagnostics."
    input_schema = DiagnosticsInput
    output_schema = DiagnosticsOutput
    permission = ToolPermissionMetadata(action="diagnostics", risk="low", is_read_only=True, allowed_in_plan_mode=True)
    runtime = ToolRuntimeMetadata(kind="diagnostics")

    def __init__(self, diagnostics_service: DiagnosticsService) -> None:
        self.diagnostics_service = diagnostics_service

    def run(self, data: DiagnosticsInput, context: ToolExecutionContext) -> DiagnosticsOutput:
        diagnostics = self.diagnostics_service.run()
        return DiagnosticsOutput(diagnostics=diagnostics, content=str(diagnostics))

