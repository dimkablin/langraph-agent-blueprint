from __future__ import annotations

from pydantic import BaseModel

from claude_code_langgraph.services.diagnostics_service import DiagnosticsService

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class DiagnosticsInput(BaseModel):
    verbose: bool = False


class DiagnosticsOutput(ToolOutput):
    diagnostics: dict[str, object]


class DiagnosticsTool(BaseTool[DiagnosticsInput, DiagnosticsOutput]):
    name = "diagnostics"
    description = "Run project and environment diagnostics."
    input_schema = DiagnosticsInput
    output_schema = DiagnosticsOutput
    safety = ToolSafety.READ_ONLY
    is_read_only = True
    requires_permission = False

    def __init__(self, diagnostics_service: DiagnosticsService) -> None:
        self.diagnostics_service = diagnostics_service

    def run(self, data: DiagnosticsInput, context: ToolExecutionContext) -> DiagnosticsOutput:
        diagnostics = self.diagnostics_service.run()
        return DiagnosticsOutput(diagnostics=diagnostics, content=str(diagnostics))

